"""
VOICEGUARD AI — Gemini Audio Analysis Service
==============================================
Sends audio to the Google Gemini API for voice authenticity analysis.
Returns a structured result that is safely consumed by the fusion engine.

IMPORTANT: This service is intentionally defensive. Any failure in this
module must not propagate to the caller — the caller should catch all
exceptions and proceed with AASIST-only results.

Score semantics in this service:
  suspicion_score: 0 = authentic, 100 = highly synthetic
  confidence: 0 = very uncertain, 100 = very confident

These are normalized into the fusion engine's direction
(spoof probability 0.0–1.0) inside fusion_engine.py.
"""

import io
import json
import logging
import os
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result type definitions (TypedDict-style for Python 3.10 compatibility)
# ---------------------------------------------------------------------------

def _make_unavailable_result(reason: str) -> dict[str, Any]:
    """Return the canonical 'Gemini unavailable' result."""
    return {
        "available": False,
        "classification": "UNCERTAIN",
        "suspicionScore": None,
        "confidence": None,
        "evidence": [],
        "suspiciousSegments": [],
        "limitations": [reason],
    }


def _make_success_result(
    classification: str,
    suspicion_score: int,
    confidence: int,
    evidence: list[str],
    suspicious_segments: list[dict],
    limitations: list[str],
) -> dict[str, Any]:
    """Return a validated, canonical Gemini success result."""
    return {
        "available": True,
        "classification": classification,
        "suspicionScore": suspicion_score,
        "confidence": confidence,
        "evidence": evidence,
        "suspiciousSegments": suspicious_segments,
        "limitations": limitations,
    }


# ---------------------------------------------------------------------------
# Gemini Prompt
# ---------------------------------------------------------------------------

ANALYSIS_PROMPT = """You are a voice-analysis assistant for a security application.
Analyze this audio clip and assess whether it contains characteristics consistent with authentic human speech or AI-generated/synthetic speech.

Analyze the following dimensions:
- Prosody and pitch variation (natural vs. monotonous/unnaturally smooth)
- Speaking rhythm and tempo consistency
- Pause patterns (natural breathing pauses vs. robotic or missing pauses)
- Articulation and phoneme transitions
- Pronunciation consistency across the recording
- Emotional expression consistency
- Presence of unnatural or robotic characteristics
- Acoustic/synthetic artifacts (spectral smearing, over-smooth formants, etc.)
- Any suspicious temporal segments if identifiable

Do NOT claim certainty when the evidence is insufficient. Use "UNCERTAIN" when the audio is ambiguous.

Return ONLY a valid JSON object (no markdown fences, no prose outside JSON) with exactly this structure:

{
  "classification": "AUTHENTIC" | "SYNTHETIC" | "UNCERTAIN",
  "suspicion_score": <integer 0-100, where 0=definitely authentic, 100=definitely synthetic>,
  "confidence": <integer 0-100, where 0=very uncertain of your assessment, 100=very confident>,
  "evidence": [<list of specific observed characteristics, max 8 items>],
  "suspicious_segments": [
    {"start": <float seconds>, "end": <float seconds>, "reason": "<description>"}
  ],
  "limitations": [<list of analytical limitations, e.g. short duration, low quality, ambient noise>]
}

IMPORTANT:
- suspicion_score and confidence MUST be integers between 0 and 100.
- classification MUST be exactly one of: AUTHENTIC, SYNTHETIC, UNCERTAIN.
- evidence list should contain concrete, specific observations, not generic statements.
- If no suspicious segments are identifiable, return an empty array for suspicious_segments.
- AI audio analysis should be treated as supporting evidence, not a definitive determination.
"""


# ---------------------------------------------------------------------------
# Gemini Audio Analyzer
# ---------------------------------------------------------------------------

class GeminiAudioAnalyzer:
    """
    Analyzes audio using the Google Gemini API.

    Usage:
        analyzer = GeminiAudioAnalyzer(api_key="...", timeout=30)
        result = analyzer.analyze(audio_bytes, mime_type="audio/wav")
    """

    SUPPORTED_MIME_TYPES = {
        "audio/wav", "audio/x-wav",
        "audio/mpeg", "audio/mp3",
        "audio/flac", "audio/x-flac",
        "audio/ogg", "audio/webm",
        "audio/aac", "audio/m4a", "audio/mp4", "audio/x-m4a",
    }
    # Gemini model to use for audio analysis.
    # gemini-3.6-flash supports native audio via Files API and JSON structured output.
    MODELS_TO_TRY = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest"]

    def __init__(self, api_key: str, timeout: int = 30):
        self._api_key = api_key
        self._timeout = timeout
        self._client = None

    def _get_client(self):
        """Lazily initialize the Gemini client."""
        if self._client is None:
            import google.genai as genai  # type: ignore
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def is_configured(self) -> bool:
        """Returns True if a non-empty API key is configured."""
        return bool(self._api_key and self._api_key.strip())

    def analyze(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> dict[str, Any]:
        """
        Analyze audio bytes using Gemini.

        Parameters:
            audio_bytes: Raw audio file bytes
            mime_type: MIME type of the audio (e.g. "audio/wav")

        Returns:
            A dict conforming to the GeminiAnalysisResult schema.
            On any failure, returns _make_unavailable_result(...).
        """
        if not self.is_configured():
            logger.warning("[Gemini] API key not configured. Skipping Gemini analysis.")
            return _make_unavailable_result("Gemini API key not configured")

        # Normalize mime type
        mime_type = mime_type.lower().split(";")[0].strip()
        if mime_type not in self.SUPPORTED_MIME_TYPES:
            logger.warning("[Gemini] Unsupported MIME type: %s", mime_type)
            return _make_unavailable_result(f"Audio format '{mime_type}' not supported by Gemini")

        try:
            return self._run_analysis(audio_bytes, mime_type)
        except Exception as exc:
            logger.error("[Gemini] Unexpected error during analysis: %s", exc, exc_info=True)
            return _make_unavailable_result("Gemini analysis failed due to an unexpected error")

    def _run_analysis(self, audio_bytes: bytes, mime_type: str) -> dict[str, Any]:
        """Internal: uploads audio and runs Gemini inference."""
        import google.genai as genai  # type: ignore
        import google.genai.types as genai_types  # type: ignore

        client = self._get_client()
        t0 = time.monotonic()

        # Upload audio via Files API (required for audio content)
        logger.info("[Gemini] Uploading audio (%d bytes, %s)...", len(audio_bytes), mime_type)
        try:
            audio_file = client.files.upload(
                file=io.BytesIO(audio_bytes),
                config=genai_types.UploadFileConfig(
                    mime_type=mime_type,
                    display_name="voiceguard_audio_analysis",
                ),
            )
        except Exception as exc:
            msg = str(exc)
            logger.error("[Gemini] File upload failed: %s", msg)
            if "API_KEY" in msg.upper() or "INVALID" in msg.upper() or "FORBIDDEN" in msg.upper():
                return _make_unavailable_result("Gemini API key is invalid or missing")
            if "QUOTA" in msg.upper() or "RATE" in msg.upper() or "429" in msg:
                # Attempt to extract retry delay
                delay = 60
                import re
                match = re.search(r'retry after (\d+)', msg.lower())
                if match:
                    try:
                        delay = int(match.group(1))
                    except ValueError:
                        pass
                return _make_unavailable_result(f"Gemini API quota or rate limit exceeded. Retry delay: {delay}s")
            return _make_unavailable_result(f"Gemini audio upload failed")

        upload_time = time.monotonic() - t0
        logger.info("[Gemini] Upload complete in %.2fs. Running analysis...", upload_time)

        response = None
        last_error = ""

        # Try models in order of preference
        try:
            for model_id in self.MODELS_TO_TRY:
                try:
                    logger.info("[Gemini] Attempting inference with %s...", model_id)
                    response = client.models.generate_content(
                        model=model_id,
                        contents=[
                            genai_types.Part.from_uri(
                                file_uri=audio_file.uri,
                                mime_type=mime_type,
                            ),
                            ANALYSIS_PROMPT,
                        ],
                        config=genai_types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.1,   # Low temperature for structured/consistent output
                            max_output_tokens=1024,
                            automatic_function_calling=genai_types.AutomaticFunctionCallingConfig(
                                disable=True
                            ),
                        ),
                    )
                    if response and response.text:
                        logger.info("[Gemini] Inference successful with %s", model_id)
                        break
                except Exception as model_exc:
                    last_error = str(model_exc)
                    logger.warning("[Gemini] Model %s failed: %s", model_id, last_error)
                    continue

            if response is None or not getattr(response, "text", None):
                logger.error("[Gemini] All models failed. Last error: %s", last_error)
                if "TIMEOUT" in last_error.upper() or "deadline" in last_error.lower():
                    return _make_unavailable_result("Gemini analysis timed out")
                if "QUOTA" in last_error.upper() or "RATE" in last_error.upper() or "429" in last_error:
                    delay = 60
                    import re
                    match = re.search(r'retry after (\d+)', last_error.lower())
                    if match:
                        try:
                            delay = int(match.group(1))
                        except ValueError:
                            pass
                    return _make_unavailable_result(f"Gemini API quota or rate limit exceeded. Retry delay: {delay}s")
                return _make_unavailable_result("Gemini inference failed")

        finally:
            # Best-effort cleanup of the uploaded file
            try:
                client.files.delete(name=audio_file.name)
                logger.debug("[Gemini] Cleaned up uploaded file: %s", audio_file.name)
            except Exception:
                pass

        total_time = time.monotonic() - t0
        logger.info("[Gemini] Analysis complete in %.2fs total.", total_time)

        # Parse and validate response
        return self._parse_response(response)

    def _parse_response(self, response) -> dict[str, Any]:
        """Parse and strictly validate the Gemini JSON response."""
        try:
            raw_text = response.text.strip()
        except (AttributeError, ValueError) as exc:
            logger.error("[Gemini] Could not extract response text: %s", exc)
            return _make_unavailable_result("Gemini returned an empty or invalid response")

        if not raw_text:
            return _make_unavailable_result("Gemini returned an empty response")

        # Attempt to extract JSON object if surrounded by markdown or noise
        import re
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if not json_match:
            # If no closing brace, it might be truncated. Try to match up to the end.
            json_match = re.search(r'\{.*', raw_text, re.DOTALL)
            if not json_match:
                return _make_unavailable_result("Gemini returned no JSON object")
            
        clean_text = json_match.group(0).strip()

        # Fix common truncated JSON by appending closing braces/brackets if missing
        open_braces = clean_text.count('{') - clean_text.count('}')
        open_brackets = clean_text.count('[') - clean_text.count(']')
        
        # Remove trailing commas before closing
        clean_text = re.sub(r',\s*$', '', clean_text)
        
        if open_brackets > 0:
            clean_text += ']' * open_brackets
        if open_braces > 0:
            clean_text += '}' * open_braces

        try:
            data = json.loads(clean_text)
        except json.JSONDecodeError as exc:
            logger.error("[Gemini] JSON parse error: %s | Cleaned: %s", exc, clean_text[:500])
            return _make_unavailable_result("Gemini returned malformed JSON")

        return self._validate_and_normalize(data)

    def _validate_and_normalize(self, data: dict) -> dict[str, Any]:
        """Validate schema and sanitize all fields."""
        if not isinstance(data, dict):
            return _make_unavailable_result("Gemini response was not a JSON object")

        # --- classification ---
        raw_cls = str(data.get("classification", "")).strip().upper()
        if raw_cls not in ("AUTHENTIC", "SYNTHETIC", "UNCERTAIN"):
            logger.warning("[Gemini] Unexpected classification '%s', defaulting to UNCERTAIN", raw_cls)
            raw_cls = "UNCERTAIN"

        # --- suspicion_score ---
        raw_score = data.get("suspicion_score", data.get("suspicionScore", None))
        try:
            suspicion_score = max(0, min(100, int(float(raw_score))))
        except (TypeError, ValueError):
            logger.warning("[Gemini] Invalid suspicion_score '%s'. Cannot reliably fuse without score.", raw_score)
            return _make_unavailable_result(f"Invalid suspicion_score from Gemini: {raw_score}")

        # --- confidence ---
        raw_conf = data.get("confidence", None)
        try:
            confidence = max(0, min(100, int(float(raw_conf))))
        except (TypeError, ValueError):
            logger.warning("[Gemini] Invalid confidence '%s', defaulting to 50", raw_conf)
            confidence = 50

        # --- evidence ---
        raw_evidence = data.get("evidence", [])
        if not isinstance(raw_evidence, list):
            raw_evidence = []
        evidence = [str(e)[:200] for e in raw_evidence if e][:10]

        # --- suspicious_segments ---
        raw_segments = data.get("suspicious_segments", data.get("suspiciousSegments", []))
        if not isinstance(raw_segments, list):
            raw_segments = []
        suspicious_segments = []
        for seg in raw_segments[:20]:
            if not isinstance(seg, dict):
                continue
            try:
                start = float(seg.get("start", 0))
                end = float(seg.get("end", 0))
                reason = str(seg.get("reason", ""))[:200]
                if end > start >= 0:
                    suspicious_segments.append({"start": start, "end": end, "reason": reason})
            except (TypeError, ValueError):
                continue

        # --- limitations ---
        raw_limits = data.get("limitations", [])
        if not isinstance(raw_limits, list):
            raw_limits = []
        limitations = [str(l)[:300] for l in raw_limits if l][:5]

        # Always add the standard disclaimer
        disclaimer = "AI-generated likelihood — treat as supporting evidence, not a definitive determination."
        if disclaimer not in limitations:
            limitations.append(disclaimer)

        return _make_success_result(
            classification=raw_cls,
            suspicion_score=suspicion_score,
            confidence=confidence,
            evidence=evidence,
            suspicious_segments=suspicious_segments,
            limitations=limitations,
        )
