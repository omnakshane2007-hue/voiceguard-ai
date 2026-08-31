import io
import logging
import os
import threading
import concurrent.futures

try:
    import torch
except ImportError:
    torch = None

import librosa
import numpy as np
from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS

from detector import DetectionSystem, winsound_alert_listener
from services.gemini_audio_analyzer import GeminiAudioAnalyzer
from services.rawnet2_analyzer import RawNet2Analyzer
from services.fusion_engine import fuse
from services.audio_preprocessor import preprocess_audio_for_aasist
import config

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Flask app & global detection system (preserved exactly from original)
# ---------------------------------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")

# ---------------------------------------------------------------------------
# CORS — allow any origin so the Vercel frontend can reach Railway backend.
# Restrict to your Vercel domains in production by setting CORS_ORIGINS env var.
# ---------------------------------------------------------------------------
_cors_origins_env = os.environ.get("CORS_ORIGINS", "*")
_cors_origins = [o.strip() for o in _cors_origins_env.split(",")] if "," in _cors_origins_env else _cors_origins_env
CORS(app, origins=_cors_origins, supports_credentials=True)

# Global detection system instance
system = DetectionSystem()
system.add_listener(winsound_alert_listener)

# ---------------------------------------------------------------------------
# Analyzers — Singletons loaded at startup
# ---------------------------------------------------------------------------
_gemini_analyzer = GeminiAudioAnalyzer(
    api_key=config.GEMINI_API_KEY,
    timeout=config.GEMINI_TIMEOUT_SECONDS,
)

# Global bounded executor for Gemini to prevent unbounded memory/rate limits
GEMINI_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2)

_rawnet2_analyzer = RawNet2Analyzer(
    weights_path=config.RAWNET2_WEIGHTS_PATH,
    config_path=config.RAWNET2_CONFIG_PATH,
)

if config.GEMINI_API_KEY:
    logger.info("[App] Gemini API key configured. Gemini analysis is ENABLED.")
else:
    logger.warning("[App] GEMINI_API_KEY is not set. Gemini analysis will be DISABLED. "
                   "Set it in your .env file to enable.")

if _rawnet2_analyzer.is_available():
    logger.info("[App] RawNet2 model loaded and ENABLED.")
else:
    logger.warning("[App] RawNet2 model is NOT available.")

# ---------------------------------------------------------------------------
# Boot AASIST model at module import time so Gunicorn workers have it loaded.
# This runs whether started via `python app.py` or `gunicorn app:app`.
# ---------------------------------------------------------------------------
def _boot_system():
    """Load AASIST model and start the detection state machine."""
    try:
        system.setup()
        system.start()
        logger.info("[Boot] DetectionSystem online. AASIST loaded: %s",
                    system.model_loader.model is not None)
    except Exception as exc:
        logger.error("[Boot] DetectionSystem failed to start: %s", exc)
        logger.warning("[Boot] Continuing without AASIST — Gemini+RawNet2 fusion only.")


_boot_system()


import time
from datetime import datetime

# (CORS is handled by flask-cors above — manual after_request hook removed)


@app.route('/health', methods=['GET', 'OPTIONS'])
@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    """Health check endpoint for frontend to verify live backend connectivity."""
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
        
    return jsonify({
        "status": "ok",
        "service": "voiceguard-live",
        "version": "2.4.1",
        "models": {
            "aasist": bool(system.model_loader.model is not None if system.model_loader else False),
            "rawnet2": bool(_rawnet2_analyzer.is_available()),
            "gemini": bool(config.GEMINI_API_KEY)
        },
        "gemini_enabled": bool(config.GEMINI_API_KEY),
        "timestamp": datetime.utcnow().isoformat()
    })


# ===========================================================================
# Original routes — preserved exactly
# ===========================================================================

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/status')
def status():
    # Maintain exact original keys and add real-time telemetry attributes
    return jsonify({
        "status": system.status,
        "current_score": float(system.current_score),
        "smoothed_score": float(system.smoothed_score),
        "speech_ratio": float(getattr(system, "last_speech_ratio", 0.0)),
        "is_recording": bool(system.audio_capture.is_recording) if system.audio_capture else False,
        "total_chunks": int(getattr(system, "total_chunks", 0)),
        "processed_chunks": int(getattr(system, "processed_chunks", 0)),
        "last_update_time": getattr(system, "last_update_time", None),
        "model_loaded": system.model_loader.model is not None if system.model_loader else False,
        "gemini_enabled": bool(config.GEMINI_API_KEY),
        "rawnet2_loaded": _rawnet2_analyzer.is_available(),
        "sample_rate": config.SAMPLE_RATE,
        "chunk_samples": config.AUDIO_CHUNK_SAMPLES,
        "suspicious_threshold": config.SUSPICIOUS_THRESHOLD,
        "high_risk_threshold": config.HIGH_RISK_THRESHOLD
    })


@app.route('/api/sample_files')
def list_sample_files():
    """List sample audio files available in root for quick testing."""
    sample_files = []
    root_dir = os.path.dirname(__file__)
    for filename in ["synthetic_spoof_test.wav", "synthetic_spoof_test (1).wav", "dummy.wav", "silence_control.wav"]:
        filepath = os.path.join(root_dir, filename)
        if os.path.exists(filepath):
            sample_files.append({
                "filename": filename,
                "size_kb": round(os.path.getsize(filepath) / 1024, 1)
            })
    return jsonify({"samples": sample_files})


@app.route('/api/sample_file/<filename>')
def get_sample_file(filename):
    """Serve sample audio files for quick browser playback/analysis."""
    root_dir = os.path.dirname(__file__)
    return send_from_directory(root_dir, filename)


# ===========================================================================
# /api/predict — Extended with Gemini + Fusion (AASIST preserved completely)
# ===========================================================================

import tempfile

ALLOWED_EXTENSIONS = {".wav", ".flac", ".mp3", ".mpeg", ".m4a", ".ogg"}
MIME_MAP = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".mpeg": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
}


def _validate_upload(file) -> tuple[str | None, str | None]:
    """
    Validate the uploaded file.
    Returns (error_message, None) on failure or (None, mime_type) on success.
    """
    if not file or file.filename == '':
        return "No selected file.", None

    filename = file.filename
    ext = os.path.splitext(filename)[1].lower() if filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}.", None

    # Sanitize filename (no path traversal)
    safe_name = os.path.basename(filename)
    if not safe_name:
        return "Invalid filename.", None

    mime_type = MIME_MAP.get(ext, "audio/wav")
    return None, mime_type


def _run_aasist(audio_bytes: bytes, filename: str = "audio.wav") -> dict:
    """
    Run AASIST analysis on raw audio bytes.
    Returns dict with 'score' (genuine_prob 0.0–1.0) and metadata,
    or raises an exception on failure.
    """
    if torch is None or system.model_loader.model is None:
        raise RuntimeError("AASIST model is not loaded or PyTorch is unavailable in this environment.")

    try:
        y, sr = librosa.load(io.BytesIO(audio_bytes), sr=config.SAMPLE_RATE, mono=True)  # type: ignore
    except Exception:
        # Fallback to temp file with appropriate extension for container formats (e.g. m4a)
        ext = os.path.splitext(filename)[1].lower() or '.wav'
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            y, sr = librosa.load(tmp_path, sr=config.SAMPLE_RATE, mono=True)  # type: ignore
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    original_samples = len(y)
    y_processed = preprocess_audio_for_aasist(y, max_len=config.AUDIO_CHUNK_SAMPLES)

    audio_tensor = torch.tensor(y_processed, dtype=torch.float32)
    score = float(system.model_loader.predict(audio_tensor))

    return {
        "score": score,
        "original_samples": original_samples,
        "duration_sec": round(original_samples / config.SAMPLE_RATE, 2),
    }


def _build_aasist_status(score: float) -> tuple[str, str]:
    """Map AASIST genuine_prob score to status string and threat label."""
    if score <= config.HIGH_RISK_THRESHOLD:
        return config.STATE_HIGH_RISK, "High Risk (Likely Cloned/Synthetic)"
    elif score <= config.SUSPICIOUS_THRESHOLD:
        return config.STATE_SUSPICIOUS, "Suspicious (Potentially Cloned)"
    else:
        return config.STATE_SAFE, "Safe (Likely Authentic)"


@app.route('/api/predict', methods=['POST'])
def predict_file():
    # --- Validate upload ---
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded. Please select an audio file."}), 400

    file = request.files['file']
    validation_error, mime_type = _validate_upload(file)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    # Read file bytes once — reused for both AASIST and Gemini
    try:
        audio_bytes = file.read()
    except Exception as exc:
        logger.error("[API] Failed to read uploaded file: %s", exc)
        return jsonify({"error": "Failed to read uploaded audio file."}), 500

    # --- Size check ---
    max_bytes = int(config.MAX_AUDIO_SIZE_MB * 1024 * 1024)
    if len(audio_bytes) > max_bytes:
        return jsonify({
            "error": f"Audio file too large ({len(audio_bytes) // (1024*1024)}MB). "
                     f"Maximum allowed: {int(config.MAX_AUDIO_SIZE_MB)}MB."
        }), 413

    filename = os.path.basename(file.filename or "audio")

    # -----------------------------------------------------------------------
    # Run AASIST, Gemini, and RawNet2 concurrently via ThreadPoolExecutor
    # -----------------------------------------------------------------------
    aasist_result = None
    aasist_error = None
    gemini_result = None
    rawnet2_result = None

    def run_aasist_task():
        nonlocal aasist_result, aasist_error
        try:
            aasist_result = _run_aasist(audio_bytes, filename=filename)
            logger.info("[API] AASIST complete: score=%.4f", aasist_result["score"])
        except Exception as exc:
            aasist_error = str(exc)
            logger.error("[API] AASIST failed: %s", exc)

    def run_gemini_task():
        nonlocal gemini_result
        # Gemini failure is always safe — analyzer returns unavailable result
        gemini_result = _gemini_analyzer.analyze(audio_bytes, mime_type=mime_type)
        logger.info(
            "[API] Gemini complete: available=%s classification=%s suspicion=%s",
            gemini_result.get("available"),
            gemini_result.get("classification"),
            gemini_result.get("suspicionScore"),
        )

    def run_rawnet2_task():
        nonlocal rawnet2_result
        # RawNet2 failure is always safe — analyzer returns unavailable result
        rawnet2_result = _rawnet2_analyzer.analyze(audio_bytes, filename=filename)
        logger.info(
            "[API] RawNet2 complete: available=%s classification=%s spoofScore=%s",
            rawnet2_result.get("available"),
            rawnet2_result.get("classification"),
            rawnet2_result.get("spoofScore"),
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(run_aasist_task),
            executor.submit(run_gemini_task),
            executor.submit(run_rawnet2_task),
        ]
        concurrent.futures.wait(futures, timeout=12.0)

    # Check if at least one model succeeded
    gemini_ok = gemini_result is not None and gemini_result.get("available", False)
    rawnet2_ok = rawnet2_result is not None and rawnet2_result.get("available", False)
    aasist_ok = aasist_result is not None

    if not (aasist_ok or gemini_ok or rawnet2_ok):
        return jsonify({
            "error": f"Audio processing failed across all models: {aasist_error or 'No model available'}"
        }), 500

    # -----------------------------------------------------------------------
    # Compute AASIST-only fields (or fall back to fusion score if AASIST unavailable)
    # -----------------------------------------------------------------------
    if aasist_ok:
        score = aasist_result["score"]
        original_samples = aasist_result["original_samples"]
        duration_sec = aasist_result["duration_sec"]
        status_val, threat_label = _build_aasist_status(score)
    else:
        # Fallback values when running in cloud serverless mode
        original_samples = 0
        duration_sec = 0.0
        score = 0.5  # Neutral fallback
        status_val = config.STATE_SAFE
        threat_label = "AASIST Offline (Using Multi-Model Fusion)"

    # -----------------------------------------------------------------------
    # 3-Model Fusion
    # -----------------------------------------------------------------------
    fusion = fuse(
        aasist_result=aasist_result if aasist_ok else None,
        gemini_result=gemini_result,
        rawnet2_result=rawnet2_result,
        aasist_weight=config.AASIST_WEIGHT,
        gemini_weight=config.GEMINI_WEIGHT,
        rawnet2_weight=config.RAWNET2_WEIGHT,
    )

    if not aasist_ok:
        # Reflect composite fusion score as primary score when AASIST is offline
        score = fusion.get("genuine_probability", 0.5)
        status_val, threat_label = _build_aasist_status(score)

    # -----------------------------------------------------------------------
    # Build response — all original fields preserved, new ones appended
    # -----------------------------------------------------------------------
    response = {
        # --- Original fields (DO NOT CHANGE) ---
        "score": score,
        "status": status_val,
        "threat_label": threat_label,
        "filename": filename,
        "samples": original_samples,
        "duration_sec": duration_sec,
        "genuine_probability_percent": round(score * 100, 2),
        "spoof_probability_percent": round((1.0 - score) * 100, 2),

        # --- Layer 2: Gemini analysis result ---
        "gemini": gemini_result,

        # --- Layer 3: RawNet2 analysis result ---
        "rawnet2": rawnet2_result,

        # --- 3-Model Fusion result ---
        "fusion": fusion,
    }

    return jsonify(response)


# ===========================================================================
# Live Streaming Audio Chunk Endpoint
# ===========================================================================

def _compute_chunk_speech_and_rms(y: np.ndarray, sr: int = 16000) -> tuple[float, float]:
    """Calculate RMS energy and speech ratio for an incoming audio chunk."""
    if y is None or len(y) == 0:
        return 0.0, 0.0
    rms = float(np.sqrt(np.mean(y**2)))
    
    # Try WebRTC VAD if installed
    try:
        import webrtcvad
        vad = webrtcvad.Vad(config.VAD_MODE)
        pcm_data = (np.clip(y, -1.0, 1.0) * 32767).astype(np.int16)
        frame_len = int(sr * 0.03)  # 30ms = 480 samples
        n_frames = len(pcm_data) // frame_len
        if n_frames == 0:
            speech_ratio = 1.0 if rms > 0.01 else 0.0
        else:
            speech_frames = sum(
                1 for i in range(n_frames)
                if vad.is_speech(pcm_data[i * frame_len : (i + 1) * frame_len].tobytes(), sr)
            )
            speech_ratio = speech_frames / float(n_frames)
    except Exception:
        # Fallback to RMS thresholding
        speech_ratio = 1.0 if rms > 0.015 else (rms / 0.015)

    return float(np.clip(speech_ratio, 0.0, 1.0)), float(rms)


@app.route('/api/live_chunk', methods=['POST', 'OPTIONS'])
def process_live_chunk():
    """
    Real-time streaming chunk ingestion endpoint.
    Accepts 16 kHz audio chunks from the browser's live microphone,
    evaluates VAD speech energy, executes available models in parallel,
    performs evidence fusion, updates the state machine, and returns structured telemetry.
    """
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    start_time = time.time()

    # 1. Extract audio bytes from multipart form or raw request body
    audio_bytes = None
    if 'file' in request.files:
        audio_bytes = request.files['file'].read()
    elif request.data:
        audio_bytes = request.data

    if not audio_bytes or len(audio_bytes) < 100:
        return jsonify({"error": "Empty audio chunk payload."}), 400

    # 2. Decode audio into 16 kHz mono waveform
    try:
        y, sr = librosa.load(io.BytesIO(audio_bytes), sr=config.SAMPLE_RATE, mono=True)
    except Exception:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            y, sr = librosa.load(tmp_path, sr=config.SAMPLE_RATE, mono=True)
        except Exception as exc:
            return jsonify({"error": f"Audio chunk decoding failed: {exc}"}), 400
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    # 3. Compute VAD speech ratio & acoustic energy
    speech_ratio, rms = _compute_chunk_speech_and_rms(y, config.SAMPLE_RATE)
    audio_level = round(float(rms), 4)

    # 4. Check if chunk contains active speech
    if speech_ratio < 0.20 and rms < 0.008:
        # Background silence or room noise -> Return low latency telemetry without heavy inference
        elapsed_ms = int((time.time() - start_time) * 1000)
        return jsonify({
            "timestamp": datetime.utcnow().isoformat(),
            "speechDetected": False,
            "speechRatio": round(speech_ratio, 3),
            "audioLevel": audio_level,
            "currentScore": float(system.current_score),
            "smoothedScore": float(system.smoothed_score),
            "state": system.status,
            "confidence": 95,
            "modelDisagreement": False,
            "processingTimeMs": elapsed_ms,
            "message": "Silence or background noise filtered by VAD."
        })

    # 5. Run available local AI models sequentially to avoid threading overhead and GIL contention
    aasist_result = None
    rawnet2_result = None

    try:
        aasist_result = _run_aasist(audio_bytes, filename="live_chunk.wav")
    except Exception as exc:
        logger.debug("[Live] AASIST unavailable: %s", exc)

    if _rawnet2_analyzer.is_available():
        try:
            rawnet2_result = _rawnet2_analyzer.analyze(audio_bytes, filename="live_chunk.wav")
        except Exception as exc:
            logger.debug("[Live] RawNet2 failed: %s", exc)

    # 6. Dispatch Gemini analysis to background executor (Non-Blocking)
    gemini_cache = system.latest_gemini_result
    gemini_status = "disabled"
    should_run_gemini = False
    current_time = time.time()
    
    if config.GEMINI_API_KEY:
        if system.is_gemini_pending:
            gemini_status = "pending"
        elif current_time < system.gemini_cooldown_until:
            gemini_status = "rate_limited"
        else:
            if gemini_cache:
                age = current_time - gemini_cache.get("timestamp", 0)
                if age > config.GEMINI_CACHE_MAX_AGE_SECONDS:
                    gemini_status = "stale"
                    gemini_cache = None  # Do not use stale cache in fusion
                elif not gemini_cache.get("available"):
                    gemini_status = "error"
                    gemini_cache = None  # Do not use error cache in fusion
                else:
                    gemini_status = "fresh"
            else:
                gemini_status = "unavailable"

            # Check if interval elapsed
            time_since_last = current_time - system.gemini_last_request_time
            if time_since_last >= config.GEMINI_LIVE_INTERVAL_SECONDS:
                should_run_gemini = True

    if should_run_gemini:
        system.is_gemini_pending = True
        system.gemini_last_request_time = current_time
        
        def _background_gemini_task(audio, mime):
            try:
                res = _gemini_analyzer.analyze(audio, mime_type=mime)
                if not res.get("available") and any("rate limit" in str(l).lower() or "quota" in str(l).lower() for l in res.get("limitations", [])):
                    logger.warning("[Gemini] Rate limited. Entering cooldown.")
                    delay = 60
                    import re
                    # Look for delay in error message embedded by analyzer
                    error_msg = res.get("error", "")
                    if not error_msg and res.get("limitations"):
                        error_msg = str(res.get("limitations")[0])
                    match = re.search(r'retry delay: (\d+)s', error_msg.lower())
                    if match:
                        try:
                            delay = int(match.group(1))
                        except ValueError:
                            pass
                    system.gemini_cooldown_until = time.time() + delay
                else:
                    res["timestamp"] = time.time()
                    system.update_gemini_result(res)
            except Exception as exc:
                logger.debug("[Live] Background Gemini failed: %s", exc)
            finally:
                system.is_gemini_pending = False

        GEMINI_EXECUTOR.submit(_background_gemini_task, audio_bytes, "audio/wav")

    # 7. Tri-Model Evidence Fusion (uses cached Gemini result only if fresh)
    fusion = fuse(
        aasist_result=aasist_result,
        gemini_result=gemini_cache,
        rawnet2_result=rawnet2_result,
        aasist_weight=config.AASIST_WEIGHT,
        gemini_weight=config.GEMINI_WEIGHT,
        rawnet2_weight=config.RAWNET2_WEIGHT,
    )

    genuine_score = float(fusion.get("genuine_probability", 0.5))
    spoof_score = float(fusion.get("finalScore", 1.0 - genuine_score))

    # Update system state & smoothed history
    current_state, smoothed_val = system.update_external_inference(genuine_score, speech_ratio)

    elapsed_ms = int((time.time() - start_time) * 1000)

    return jsonify({
        "timestamp": datetime.utcnow().isoformat(),
        "speechDetected": True,
        "speechRatio": round(speech_ratio, 3),
        "audioLevel": audio_level,
        "aasistScore": round(float(aasist_result["score"]), 4) if aasist_result else None,
        "rawnet2Score": round(float(rawnet2_result["spoofScore"]), 4) if (rawnet2_result and rawnet2_result.get("spoofScore") is not None) else None,
        "geminiScore": round(float(gemini_cache["suspicionScore"] / 100.0), 4) if (gemini_cache and gemini_cache.get("suspicionScore") is not None) else None,
        "fusionScore": round(spoof_score, 4),
        "smoothedScore": round(smoothed_val, 4),
        "modelDisagreement": bool(fusion.get("modelDisagreement", False)),
        "state": current_state,
        "confidence": int(fusion.get("confidence", 90)),
        "processingTimeMs": elapsed_ms,
        "geminiStatus": gemini_status,
        "models": {
            "aasist": aasist_result is not None,
            "rawnet2": rawnet2_result is not None and rawnet2_result.get("available", False),
            "gemini": gemini_cache is not None and gemini_cache.get("available", False)
        },
        "fusion": fusion
    })


# ===========================================================================
# Report Routes
# ===========================================================================

@app.route('/report')
def view_report():
    """Serve the comprehensive project report HTML."""
    root_dir = os.path.dirname(__file__)
    return send_from_directory(root_dir, "VOICEGUARD_AI_Project_Report.html")


@app.route('/report/pdf')
def download_pdf_report():
    """Serve the compiled PDF report for download."""
    root_dir = os.path.dirname(__file__)
    pdf_path = os.path.join(root_dir, "VOICEGUARD_AI_Project_Report.pdf")
    if os.path.exists(pdf_path):
        return send_from_directory(root_dir, "VOICEGUARD_AI_Project_Report.pdf", as_attachment=True)
    return jsonify({"error": "PDF report not yet generated on server."}), 404


# ===========================================================================
# Startup
# ===========================================================================

if __name__ == '__main__':
    # DetectionSystem already booted via _boot_system() at module load.
    # Just start the Flask dev server.
    port = int(os.environ.get('PORT', 5000))
    try:
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Failed to start Flask dev server: {e}")
    finally:
        system.stop()

