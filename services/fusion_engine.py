"""
VOICEGUARD AI — Multi-Model Evidence Fusion Engine
===================================================
Combines AASIST, Gemini, and RawNet2 scores into a single normalized risk assessment.

SCORE DIRECTION CONVENTION (used throughout this module):
  spoof_prob: 0.0 = definitely genuine / authentic, 1.0 = definitely synthetic / spoofed
  genuine_prob: inverse of spoof_prob (1.0 - spoof_prob)

Model score semantics:
  1. AASIST (from model_loader.py):
     returns genuine_probability (Class 1 = Bonafide)
     aasist_spoof = 1.0 - aasist_score

  2. Gemini (from gemini_audio_analyzer.py):
     returns suspicionScore ∈ [0, 100] (0 = authentic, 100 = synthetic)
     gemini_spoof = suspicionScore / 100.0

  3. RawNet2 (from rawnet2_analyzer.py):
     returns spoofScore ∈ [0.0, 1.0] (0.0 = authentic, 1.0 = synthetic)
     rawnet2_spoof = spoofScore

Multi-Model Fusion (weights configurable, dynamically renormalized):
  When all 3 available:
    final_spoof = aasist_spoof * W_AASIST + gemini_spoof * W_GEMINI + rawnet2_spoof * W_RAWNET2
  When any model fails or is unavailable:
    Engine automatically drops the failed model and renormalizes the weights of
    the available models to sum to 1.0. A failed model is NEVER treated as 0 score.

Final genuine_probability = 1.0 - final_spoof
"""

import logging
from typing import Any

import config

logger = logging.getLogger(__name__)


def _get_thresholds() -> tuple[float, float]:
    """Read risk thresholds from config at call time (supports live .env reloads)."""
    return config.FUSION_LOW_RISK_THRESHOLD, config.FUSION_HIGH_RISK_THRESHOLD


def fuse(
    aasist_result: dict[str, Any] | None,
    gemini_result: dict[str, Any] | None,
    rawnet2_result: dict[str, Any] | None = None,
    aasist_weight: float = 0.34,
    gemini_weight: float = 0.33,
    rawnet2_weight: float = 0.33,
) -> dict[str, Any]:
    """
    Fuse AASIST, Gemini, and RawNet2 results into a single normalized risk score.

    Parameters:
        aasist_result: Dict with 'score' key (genuine_probability 0.0–1.0) or None.
        gemini_result: Dict from GeminiAudioAnalyzer.analyze() or None.
        rawnet2_result: Dict from RawNet2Analyzer.analyze() or None.
        aasist_weight: Configured weight for AASIST (default 0.34).
        gemini_weight: Configured weight for Gemini (default 0.33).
        rawnet2_weight: Configured weight for RawNet2 (default 0.33).

    Returns:
        FusionResult dict with normalized keys:
            finalScore        float  0.0–1.0 (genuine probability)
            finalSpoof        float  0.0–1.0 (spoof probability)
            finalScorePercent float  0–100   (genuine percent, UI-friendly)
            aasistScore       float | None (genuine prob)
            aasistSpoof       float | None (spoof prob)
            geminiSpoof       float | None (spoof prob)
            rawnet2Spoof      float | None (spoof prob)
            aasistWeight      float  actual weight used after renormalization
            geminiWeight      float  actual weight used after renormalization
            rawnet2Weight     float  actual weight used after renormalization
            classification    str   HIGH_RISK | SUSPICIOUS | SAFE
            confidence        int   0–100 combined confidence
            modelsUsed        list  names of models that contributed
            modelDisagreement   bool  True when any model's verdict differs from fusion verdict
            disagreementCount   int   number of models that disagree with fusion verdict
            individualVerdicts  dict  per-model classification (never suppressed)
            lowRiskThreshold    float active FUSION_LOW_RISK_THRESHOLD value
            highRiskThreshold   float active FUSION_HIGH_RISK_THRESHOLD value
    """
    # 1. Extract standardized spoof scores
    aasist_genuine = _extract_aasist_score(aasist_result)
    gemini_spoof = _extract_gemini_spoof(gemini_result)
    rawnet2_spoof = _extract_rawnet2_spoof(rawnet2_result)

    aasist_available = (aasist_genuine is not None)
    gemini_available = (gemini_spoof is not None)
    rawnet2_available = (rawnet2_spoof is not None)

    # Convert AASIST genuine -> spoof direction
    aasist_spoof = (1.0 - aasist_genuine) if aasist_available else None

    # 2. Dynamically renormalize weights for available models
    model_availability = {
        "AASIST": (aasist_available, aasist_weight, aasist_spoof),
        "Gemini": (gemini_available, gemini_weight, gemini_spoof),
        "RawNet2": (rawnet2_available, rawnet2_weight, rawnet2_spoof),
    }

    actual_weights, models_used = _compute_dynamic_weights(model_availability)

    # 3. Compute weighted average over available models
    active_values = [
        model_availability[m][2] for m in models_used
    ]
    active_weights = [
        actual_weights[m] for m in models_used
    ]

    if active_values and sum(active_weights) > 0:
        final_spoof = sum(v * w for v, w in zip(active_values, active_weights))
    else:
        # Fallback when all models fail
        logger.error("[Fusion] All anti-spoofing models unavailable. Falling back to neutral score.")
        final_spoof = 0.5

    # Clamp scores to [0.0, 1.0]
    final_spoof = max(0.0, min(1.0, float(final_spoof)))
    final_genuine = 1.0 - final_spoof

    classification = _classify(final_spoof)

    # 4. Detect model disagreement — compare each available model's individual
    #    verdict against the fusion verdict. Disagreement is transparent and
    #    preserved in the response; it is NEVER suppressed.
    individual_verdicts = {}
    if aasist_available:
        individual_verdicts["AASIST"] = _classify(aasist_spoof)  # type: ignore[arg-type]
    if gemini_available:
        individual_verdicts["Gemini"] = _classify(gemini_spoof)  # type: ignore[arg-type]
    if rawnet2_available:
        individual_verdicts["RawNet2"] = _classify(rawnet2_spoof)  # type: ignore[arg-type]

    disagreement_count = sum(
        1 for v in individual_verdicts.values() if v != classification
    )
    model_disagreement = disagreement_count > 0

    # 5. Calculate combined confidence score
    confidence = _calculate_combined_confidence(
        aasist_available=aasist_available,
        gemini_result=gemini_result,
        rawnet2_result=rawnet2_result,
        actual_weights=actual_weights,
        models_used=models_used,
    )

    logger.info(
        "[Fusion] Models: %s | Spoof scores: AASIST=%s Gemini=%s RawNet2=%s -> final_spoof=%.4f (%s) | disagreement=%s",
        models_used,
        f"{aasist_spoof:.3f}" if aasist_spoof is not None else "N/A",
        f"{gemini_spoof:.3f}" if gemini_spoof is not None else "N/A",
        f"{rawnet2_spoof:.3f}" if rawnet2_spoof is not None else "N/A",
        final_spoof,
        classification,
        model_disagreement,
    )

    return {
        # --- Core fusion scores ---
        "finalScore": round(final_genuine, 4),
        "finalSpoof": round(final_spoof, 4),
        "finalScorePercent": round(final_genuine * 100, 1),
        # --- Individual model spoof scores (preserved, never hidden) ---
        "aasistScore": round(aasist_genuine, 4) if aasist_genuine is not None else None,
        "aasistSpoof": round(aasist_spoof, 4) if aasist_spoof is not None else None,
        "geminiSpoof": round(gemini_spoof, 4) if gemini_spoof is not None else None,
        "rawnet2Spoof": round(rawnet2_spoof, 4) if rawnet2_spoof is not None else None,
        # --- Weights actually used (after renormalization) ---
        "aasistWeight": round(actual_weights.get("AASIST", 0.0), 3),
        "geminiWeight": round(actual_weights.get("Gemini", 0.0), 3),
        "rawnet2Weight": round(actual_weights.get("RawNet2", 0.0), 3),
        # --- Classification & confidence ---
        "classification": classification,
        "confidence": confidence,
        "modelsUsed": models_used,
        # --- Disagreement transparency (never suppressed) ---
        "modelDisagreement": model_disagreement,
        "disagreementCount": disagreement_count,
        "individualVerdicts": individual_verdicts,
        # --- Active risk thresholds (for UI display) ---
        "lowRiskThreshold": round(config.FUSION_LOW_RISK_THRESHOLD, 2),
        "highRiskThreshold": round(config.FUSION_HIGH_RISK_THRESHOLD, 2),
    }


# ---------------------------------------------------------------------------
# Internal Helpers & Score Extractors
# ---------------------------------------------------------------------------

def _extract_aasist_score(aasist_result: dict | None) -> float | None:
    """Extract genuine probability [0.0–1.0] from AASIST result dict."""
    if not aasist_result:
        return None
    score = aasist_result.get("score")
    if score is None:
        return None
    try:
        val = float(score)
        return max(0.0, min(1.0, val))
    except (TypeError, ValueError):
        return None


def _extract_gemini_spoof(gemini_result: dict | None) -> float | None:
    """Extract spoof probability [0.0–1.0] from Gemini result dict."""
    if not gemini_result or not gemini_result.get("available", False):
        return None
    score = gemini_result.get("suspicionScore")
    if score is None:
        return None
    try:
        val = float(score) / 100.0
        return max(0.0, min(1.0, val))
    except (TypeError, ValueError):
        return None


def _extract_rawnet2_spoof(rawnet2_result: dict | None) -> float | None:
    """Extract spoof probability [0.0–1.0] from RawNet2 result dict."""
    if not rawnet2_result or not rawnet2_result.get("available", False):
        return None
    score = rawnet2_result.get("spoofScore")
    if score is None:
        return None
    try:
        val = float(score)
        return max(0.0, min(1.0, val))
    except (TypeError, ValueError):
        return None


def _compute_dynamic_weights(
    model_data: dict[str, tuple[bool, float, float | None]]
) -> tuple[dict[str, float], list[str]]:
    """
    Dynamically renormalize weights for available models.
    Returns:
        (actual_weights_dict, models_used_list)
    """
    available_models = [
        name for name, (is_avail, weight, val) in model_data.items()
        if is_avail and val is not None
    ]

    actual_weights = {name: 0.0 for name in model_data}

    if not available_models:
        return actual_weights, []

    total_nominal_weight = sum(model_data[name][1] for name in available_models)
    if total_nominal_weight <= 0:
        total_nominal_weight = 1.0

    for name in available_models:
        actual_weights[name] = model_data[name][1] / total_nominal_weight

    return actual_weights, available_models


def _classify(final_spoof: float) -> str:
    """Map final spoof probability to a VOICEGUARD state label.
    Thresholds are read from config at call time — configurable via environment.
    """
    low_thresh, high_thresh = _get_thresholds()
    if final_spoof >= high_thresh:
        return "HIGH_RISK"
    elif final_spoof >= low_thresh:
        return "SUSPICIOUS"
    else:
        return "SAFE"


def _calculate_combined_confidence(
    aasist_available: bool,
    gemini_result: dict | None,
    rawnet2_result: dict | None,
    actual_weights: dict[str, float],
    models_used: list[str],
) -> int:
    """
    Compute a weighted aggregate confidence percentage [0–100].
    """
    if not models_used:
        return 0

    confidences = {}
    if aasist_available:
        confidences["AASIST"] = 85.0

    if gemini_result and gemini_result.get("available") and gemini_result.get("confidence") is not None:
        try:
            confidences["Gemini"] = float(gemini_result["confidence"])
        except (TypeError, ValueError):
            confidences["Gemini"] = 70.0

    if rawnet2_result and rawnet2_result.get("available") and rawnet2_result.get("confidence") is not None:
        try:
            confidences["RawNet2"] = float(rawnet2_result["confidence"])
        except (TypeError, ValueError):
            confidences["RawNet2"] = 80.0

    total_conf = sum(
        confidences.get(m, 75.0) * actual_weights.get(m, 0.0)
        for m in models_used
    )

    return max(0, min(100, round(total_conf)))
