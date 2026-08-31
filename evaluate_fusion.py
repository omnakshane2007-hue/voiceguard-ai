"""
VOICEGUARD AI — Fusion Calibration Evaluation Script
=====================================================
Runs AASIST and RawNet2 on all available audio samples (genuine + synthetic).
Gemini is called live where the API key is present; if unavailable, the sample
is marked as Gemini=UNAVAILABLE and the fusion renormalizes remaining models.
Mocked Gemini scores are NEVER used for official fusion metrics.

DISCLAIMER
----------
This evaluation is based on 7-8 available samples. All metrics reported are
PRELIMINARY / ILLUSTRATIVE — the sample size is far below the threshold
needed for statistically reliable results. These numbers CANNOT be generalized
and MUST NOT be used to claim accuracy improvements.

Tested weight sets are labeled "best-performing on available dataset", NOT
"optimal" or "scientifically validated". Production weights remain unchanged
at AASIST=0.34, Gemini=0.33, RawNet2=0.33 unless explicitly approved.

Usage:
    .venv\\Scripts\\python.exe evaluate_fusion.py [--csv output.csv]
"""

import argparse
import csv
import io
import os
import sys
import time
import warnings

# Force UTF-8 output on Windows terminals (avoids cp1252 UnicodeEncodeError)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import librosa
import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(__file__))
import config
from model_loader import AASISTLoader
from services.audio_preprocessor import preprocess_audio_for_aasist
from services.rawnet2_analyzer import RawNet2Analyzer
from services.gemini_audio_analyzer import GeminiAudioAnalyzer
from services.fusion_engine import fuse

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Dataset definition — ground truth labels
# ---------------------------------------------------------------------------
DATASET = [
    # (filepath, ground_truth)  ground_truth: "GENUINE" or "SPOOF"
    ("whatsapp_test_audio.mpeg",          "GENUINE"),
    ("whatsapp_test_audio2.mpeg",         "GENUINE"),
    ("human_libri1_male.wav",             "GENUINE"),
    ("human_libri2_male.wav",             "GENUINE"),
    ("human_libri3_female.wav",           "GENUINE"),
    ("synthetic_spoof_test.wav",          "SPOOF"),
    ("synthetic_spoof_test (1).wav",      "SPOOF"),
    ("dummy.wav",                         "SPOOF"),
]

# Weight sets to test (AASIST, Gemini, RawNet2)
WEIGHT_SETS = {
    "Production (0.34/0.33/0.33)": (0.34, 0.33, 0.33),
    "AASIST-heavy  (0.50/0.25/0.25)": (0.50, 0.25, 0.25),
    "AASIST-heavy  (0.45/0.30/0.25)": (0.45, 0.30, 0.25),
    "AASIST-heavy  (0.40/0.30/0.30)": (0.40, 0.30, 0.30),
    "Equal weights (0.33/0.33/0.33)": (0.33, 0.33, 0.33),
}

# Risk thresholds to evaluate (spoof-probability based)
THRESHOLD_SETS = {
    "Conservative  (low=0.40, high=0.70)": (0.40, 0.70),
    "Balanced      (low=0.35, high=0.65)": (0.35, 0.65),
    "Strict        (low=0.30, high=0.60)": (0.30, 0.60),
}

# High-risk spoof threshold used to determine binary pred: >= this → SPOOF prediction
BINARY_HIGH_RISK = 0.70


def load_audio(filepath: str) -> tuple[np.ndarray, bytes]:
    """Load audio and return (numpy waveform, raw bytes)."""
    import tempfile
    with open(filepath, "rb") as f:
        audio_bytes = f.read()

    try:
        y, _ = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)
    except Exception:
        ext = os.path.splitext(filepath)[1].lower() or ".wav"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            y, _ = librosa.load(tmp_path, sr=16000, mono=True)
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    return y, audio_bytes


def run_aasist(y: np.ndarray, aasist_model, device) -> float:
    """Run AASIST and return genuine probability (0.0–1.0)."""
    proc = preprocess_audio_for_aasist(y)
    t = torch.tensor(proc, dtype=torch.float32).unsqueeze(0).to(device)
    with torch.no_grad():
        _, out = aasist_model(t)
        probs = F.softmax(out, dim=1)
        return probs[0, 1].item()


def compute_metrics(results: list[dict], threshold: float) -> dict:
    """
    Compute binary classification metrics using final_spoof >= threshold as SPOOF prediction.
    Returns dict with accuracy, precision, recall, f1, fpr, fnr.
    """
    tp = fp = tn = fn = 0
    for r in results:
        pred_spoof = r["fusion_spoof"] >= threshold
        true_spoof = r["ground_truth"] == "SPOOF"
        if pred_spoof and true_spoof:
            tp += 1
        elif pred_spoof and not true_spoof:
            fp += 1
        elif not pred_spoof and true_spoof:
            fn += 1
        else:
            tn += 1

    total = len(results)
    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    return {
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "accuracy": accuracy, "precision": precision,
        "recall": recall, "f1": f1, "fpr": fpr, "fnr": fnr,
    }


def print_separator(char="─", width=100):
    print(char * width)


def main():
    parser = argparse.ArgumentParser(description="VoiceGuard Fusion Calibration Evaluation")
    parser.add_argument("--csv", default="", help="Path to write results CSV (optional)")
    parser.add_argument("--no-gemini", action="store_true", help="Skip Gemini API calls entirely")
    args = parser.parse_args()

    # ── Load models ──────────────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("VOICEGUARD AI — FUSION CALIBRATION EVALUATION")
    print("=" * 100)
    print()
    print("⚠  PRELIMINARY / ILLUSTRATIVE — insufficient dataset for generalization.")
    print("   Results are based on a small convenience sample and CANNOT be used")
    print("   to claim accuracy improvements or to validate production weights.")
    print()

    print("[1/3] Loading AASIST model...")
    loader = AASISTLoader()
    loader.setup()
    device = loader.device
    aasist_model = loader.model

    print("[2/3] Loading RawNet2 model...")
    rawnet2 = RawNet2Analyzer(
        weights_path=config.RAWNET2_WEIGHTS_PATH,
        config_path=config.RAWNET2_CONFIG_PATH,
    )

    print("[3/3] Preparing Gemini analyzer...")
    use_gemini = bool(config.GEMINI_API_KEY) and not args.no_gemini
    gemini = GeminiAudioAnalyzer(
        api_key=config.GEMINI_API_KEY,
        timeout=config.GEMINI_TIMEOUT_SECONDS,
    ) if use_gemini else None

    if use_gemini:
        print("    Gemini: ENABLED (live API calls, real scores)")
    else:
        print("    Gemini: DISABLED — will be excluded from fusion (renormalized)")

    print()

    # ── Run each sample ───────────────────────────────────────────────────────
    print_separator("═")
    print("SAMPLE-LEVEL RESULTS")
    print_separator("═")

    sample_results = []
    skipped = []

    for filepath, ground_truth in DATASET:
        full_path = os.path.join(os.path.dirname(__file__), filepath)
        if not os.path.exists(full_path):
            skipped.append(filepath)
            continue

        print(f"\n  File: {filepath}  [{ground_truth}]")

        try:
            y, audio_bytes = load_audio(full_path)
        except Exception as exc:
            print(f"    ✗ Audio load failed: {exc}")
            skipped.append(filepath)
            continue

        duration_sec = len(y) / 16000
        rms = float(np.sqrt(np.mean(y ** 2)))
        print(f"    Duration: {duration_sec:.2f}s | RMS: {rms:.4f} | Samples: {len(y)}")

        # AASIST
        try:
            aasist_genuine = run_aasist(y, aasist_model, device)
            aasist_spoof = 1.0 - aasist_genuine
            print(f"    AASIST     → Genuine: {aasist_genuine*100:.2f}% | Spoof: {aasist_spoof*100:.2f}%")
        except Exception as exc:
            print(f"    AASIST     → ERROR: {exc}")
            skipped.append(filepath)
            continue

        # RawNet2
        try:
            r2 = rawnet2.analyze(audio_bytes, filename=filepath)
            rawnet2_spoof_val = r2.get("spoofScore") if r2.get("available") else None
            if rawnet2_spoof_val is not None:
                print(f"    RawNet2    → Spoof: {rawnet2_spoof_val*100:.2f}% | Classification: {r2.get('classification')}")
            else:
                print(f"    RawNet2    → UNAVAILABLE")
        except Exception as exc:
            print(f"    RawNet2    → ERROR: {exc}")
            r2 = {"available": False}

        # Gemini (live or skipped — never mocked)
        gemini_result = {"available": False}
        if use_gemini and gemini is not None:
            ext = os.path.splitext(filepath)[1].lower() or ".wav"
            mime_map = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".mpeg": "audio/mpeg",
                        ".m4a": "audio/mp4", ".flac": "audio/flac", ".ogg": "audio/ogg"}
            mime = mime_map.get(ext, "audio/wav")
            try:
                gemini_result = gemini.analyze(audio_bytes, mime_type=mime)
                if gemini_result.get("available"):
                    susp = gemini_result.get("suspicionScore", "N/A")
                    cls = gemini_result.get("classification", "N/A")
                    print(f"    Gemini     → Suspicion: {susp}% | Classification: {cls}  [REAL SCORE]")
                else:
                    print(f"    Gemini     → UNAVAILABLE (API failed, renormalizing)")
            except Exception as exc:
                print(f"    Gemini     → ERROR: {exc} (renormalizing)")
                gemini_result = {"available": False}
        else:
            print(f"    Gemini     → SKIPPED (disabled, renormalizing)")

        # Fusion with production weights
        fusion = fuse(
            aasist_result={"score": aasist_genuine},
            gemini_result=gemini_result,
            rawnet2_result=r2,
            aasist_weight=config.AASIST_WEIGHT,
            gemini_weight=config.GEMINI_WEIGHT,
            rawnet2_weight=config.RAWNET2_WEIGHT,
        )

        disagreement_note = " ⚠ MODEL DISAGREE" if fusion.get("modelDisagreement") else ""
        print(f"    FUSION     → Spoof: {fusion['finalSpoof']*100:.2f}% | Classification: {fusion['classification']}{disagreement_note}")
        if fusion.get("modelDisagreement"):
            verdicts = fusion.get("individualVerdicts", {})
            print(f"               Individual verdicts: {verdicts}")

        sample_results.append({
            "filename": filepath,
            "ground_truth": ground_truth,
            "duration_sec": round(duration_sec, 2),
            "aasist_genuine": round(aasist_genuine, 4),
            "aasist_spoof": round(aasist_spoof, 4),
            "gemini_spoof": round(gemini_result.get("suspicionScore", 0) / 100.0, 4)
                            if gemini_result.get("available") else None,
            "gemini_available": gemini_result.get("available", False),
            "rawnet2_spoof": round(r2.get("spoofScore", 0), 4) if r2.get("available") else None,
            "rawnet2_available": r2.get("available", False),
            "fusion_spoof": round(fusion["finalSpoof"], 4),
            "fusion_classification": fusion["classification"],
            "models_used": "+".join(fusion.get("modelsUsed", [])),
            "model_disagreement": fusion.get("modelDisagreement", False),
        })

        time.sleep(0.5)  # small pause between samples

    # ── Summary tables ────────────────────────────────────────────────────────
    n_genuine = sum(1 for r in sample_results if r["ground_truth"] == "GENUINE")
    n_spoof = sum(1 for r in sample_results if r["ground_truth"] == "SPOOF")
    n_total = len(sample_results)

    print()
    print_separator("═")
    print(f"DATASET SUMMARY  (N={n_total}  |  Genuine={n_genuine}  |  Spoof={n_spoof}  |  Skipped={len(skipped)})")
    if skipped:
        print(f"  Skipped files: {', '.join(skipped)}")
    print()
    print("⚠  N={} is below the minimum required for statistically reliable metrics.".format(n_total))
    print("   All metrics below are ILLUSTRATIVE ONLY.".format(n_total))
    print_separator("═")

    if n_total == 0:
        print("No samples were evaluated. Exiting.")
        return

    # ── Per-weight-set metric table ───────────────────────────────────────────
    print()
    print("WEIGHT SET EVALUATION  (threshold for binary prediction: spoof >= {:.0%})".format(BINARY_HIGH_RISK))
    print_separator()

    weight_metrics = {}
    header = f"{'Weight Set':<42} {'Acc':>6} {'Prec':>6} {'Recall':>6} {'F1':>6} {'FPR':>6} {'FNR':>6} {'TP':>4} {'FP':>4} {'TN':>4} {'FN':>4}"
    print(header)
    print_separator("-")

    for label, (wa, wg, wr) in WEIGHT_SETS.items():
        # Re-run fusion for this weight set on cached per-sample scores
        scored = []
        for r in sample_results:
            # Build synthetic result dicts from cached scores
            a_result = {"score": 1.0 - r["aasist_spoof"]}
            g_result = {
                "available": r["gemini_available"],
                "suspicionScore": round((r["gemini_spoof"] or 0) * 100),
            } if r["gemini_available"] else {"available": False}
            rn_result = {
                "available": r["rawnet2_available"],
                "spoofScore": r["rawnet2_spoof"],
            } if r["rawnet2_available"] else {"available": False}

            f = fuse(
                aasist_result=a_result,
                gemini_result=g_result,
                rawnet2_result=rn_result,
                aasist_weight=wa,
                gemini_weight=wg,
                rawnet2_weight=wr,
            )
            scored.append({"ground_truth": r["ground_truth"], "fusion_spoof": f["finalSpoof"]})

        m = compute_metrics(scored, BINARY_HIGH_RISK)
        weight_metrics[label] = m

        print(f"{label:<42} {m['accuracy']:>6.1%} {m['precision']:>6.1%} {m['recall']:>6.1%} "
              f"{m['f1']:>6.1%} {m['fpr']:>6.1%} {m['fnr']:>6.1%} "
              f"{m['TP']:>4} {m['FP']:>4} {m['TN']:>4} {m['FN']:>4}")

    print_separator("-")

    # ── Best-performing weight set on this dataset ────────────────────────────
    # Sort by F1 then accuracy (higher = better)
    best_label = max(weight_metrics, key=lambda k: (weight_metrics[k]["f1"], weight_metrics[k]["accuracy"]))
    best_m = weight_metrics[best_label]
    print()
    print(f"Best-performing weights on available dataset: {best_label}")
    print("NOTE: This is NOT 'optimal' or 'scientifically validated'.")
    print("      It is the weight set with highest F1 on this specific convenience sample.")
    print("      Production weights remain unchanged at AASIST=0.34, Gemini=0.33, RawNet2=0.33")
    print("      until explicitly approved based on a larger, held-out evaluation dataset.")

    # ── Threshold sensitivity ─────────────────────────────────────────────────
    print()
    print_separator("═")
    print("RISK THRESHOLD SENSITIVITY  (using production weights 0.34/0.33/0.33)")
    print_separator()

    thresh_header = f"{'Threshold Set':<46} {'Acc':>6} {'Prec':>6} {'Recall':>6} {'F1':>6} {'FPR':>6} {'FNR':>6}"
    print(thresh_header)
    print_separator("-")

    prod_scored = []
    for r in sample_results:
        a_result = {"score": 1.0 - r["aasist_spoof"]}
        g_result = {"available": r["gemini_available"],
                    "suspicionScore": round((r["gemini_spoof"] or 0) * 100)} if r["gemini_available"] else {"available": False}
        rn_result = {"available": r["rawnet2_available"],
                     "spoofScore": r["rawnet2_spoof"]} if r["rawnet2_available"] else {"available": False}
        f = fuse(
            aasist_result=a_result,
            gemini_result=g_result,
            rawnet2_result=rn_result,
            aasist_weight=config.AASIST_WEIGHT,
            gemini_weight=config.GEMINI_WEIGHT,
            rawnet2_weight=config.RAWNET2_WEIGHT,
        )
        prod_scored.append({"ground_truth": r["ground_truth"], "fusion_spoof": f["finalSpoof"]})

    for label, (low_t, high_t) in THRESHOLD_SETS.items():
        m = compute_metrics(prod_scored, high_t)
        print(f"{label:<46} {m['accuracy']:>6.1%} {m['precision']:>6.1%} {m['recall']:>6.1%} "
              f"{m['f1']:>6.1%} {m['fpr']:>6.1%} {m['fnr']:>6.1%}")

    print_separator("-")
    print("NOTE: Threshold values are illustrative. Statistical significance cannot be")
    print("      established on this dataset. Current defaults (low=0.40, high=0.70)")
    print("      are configurable via FUSION_LOW_RISK_THRESHOLD and FUSION_HIGH_RISK_THRESHOLD")
    print("      environment variables without code changes.")

    # ── Model availability summary ────────────────────────────────────────────
    print()
    print_separator("═")
    print("MODEL AVAILABILITY PER SAMPLE")
    print_separator()
    header2 = f"{'File':<40} {'GT':>8} {'AASIST':>8} {'Gemini':>8} {'RawNet2':>8} {'Disagreement':>14}"
    print(header2)
    print_separator("-")
    for r in sample_results:
        gem_str = "REAL" if r["gemini_available"] else "UNAVAIL"
        rn_str = "REAL" if r["rawnet2_available"] else "UNAVAIL"
        dis_str = "⚠ YES" if r["model_disagreement"] else "NO"
        models_note = r.get("models_used", "")
        print(f"{r['filename'][:40]:<40} {r['ground_truth']:>8} {'REAL':>8} {gem_str:>8} {rn_str:>8} {dis_str:>14}")

    # ── Final recommendation ──────────────────────────────────────────────────
    prod_m = weight_metrics.get("Production (0.34/0.33/0.33)", {})
    print()
    print_separator("═")
    print("FINAL REPORT")
    print_separator("═")
    print(f"  Dataset size:           {n_total} samples  (PRELIMINARY — not sufficient for generalization)")
    print(f"  Genuine samples:        {n_genuine}")
    print(f"  Spoof samples:          {n_spoof}")
    print(f"  Skipped:                {len(skipped)}")
    print()
    print(f"  Current production weights: AASIST=0.34  Gemini=0.33  RawNet2=0.33")
    if prod_m:
        print(f"  Production performance (illustrative):")
        print(f"    Accuracy:  {prod_m['accuracy']:.1%}   Precision: {prod_m['precision']:.1%}   Recall: {prod_m['recall']:.1%}")
        print(f"    F1:        {prod_m['f1']:.1%}   FPR:       {prod_m['fpr']:.1%}   FNR:    {prod_m['fnr']:.1%}")
    print()
    print(f"  Best-performing weights on available dataset: {best_label}")
    print(f"    Accuracy:  {best_m['accuracy']:.1%}   Precision: {best_m['precision']:.1%}   Recall: {best_m['recall']:.1%}")
    print(f"    F1:        {best_m['f1']:.1%}   FPR:       {best_m['fpr']:.1%}   FNR:    {best_m['fnr']:.1%}")
    print()
    print(f"  Configurable thresholds (via .env or environment):")
    print(f"    FUSION_LOW_RISK_THRESHOLD  = {config.FUSION_LOW_RISK_THRESHOLD}")
    print(f"    FUSION_HIGH_RISK_THRESHOLD = {config.FUSION_HIGH_RISK_THRESHOLD}")
    print()
    print("  ─── RECOMMENDATION ────────────────────────────────────────────────────────")
    print("  Production weights SHOULD REMAIN UNCHANGED.")
    print("  Reason: N={} is too small to justify any weight change.".format(n_total))
    print("  The 'best-performing' set above may simply overfit to the 7-8 available")
    print("  samples. Gemini was {}available for all samples during this run.".format(
        "" if all(r["gemini_available"] for r in sample_results) else "NOT "))
    print("  Collect ≥100 diverse, held-out samples before reconsidering production weights.")
    print("  ────────────────────────────────────────────────────────────────────────────")
    print()
    print("  Known Limitations:")
    print("  - N={}. No held-out test set. Metrics are overfit to available samples.".format(n_total))
    print("  - Gemini is a live API model; scores may vary across calls.")
    print("  - LibriSpeech samples are studio audio. Real-world variance is higher.")
    print("  - WhatsApp MPEG codec and AGC artifacts may not generalise to all phones.")
    print("  - Synthetic samples are simple tone+clone, not diverse TTS/voice-cloning corpus.")
    print()

    # ── Optional CSV export ───────────────────────────────────────────────────
    if args.csv:
        fieldnames = ["filename", "ground_truth", "duration_sec", "aasist_genuine",
                      "aasist_spoof", "gemini_spoof", "gemini_available",
                      "rawnet2_spoof", "rawnet2_available", "fusion_spoof",
                      "fusion_classification", "models_used", "model_disagreement"]
        with open(args.csv, "w", newline="", encoding="utf-8") as f_csv:
            writer = csv.DictWriter(f_csv, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sample_results)
        print(f"  Results written to: {args.csv}")


if __name__ == "__main__":
    main()
