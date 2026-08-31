import os

# Load .env file if present (must happen before reading env vars)
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=False)
except ImportError:
    pass  # python-dotenv not yet installed — env vars will still be read from the OS environment

# ============================================================
# Model & Audio Config (preserved exactly from original)
# ============================================================
AASIST_REPO_URL = "https://github.com/clovaai/aasist.git"
AASIST_DIR = os.path.join(os.path.dirname(__file__), "aasist")
MODEL_WEIGHTS_PATH = os.path.join(AASIST_DIR, "models", "weights", "AASIST.pth")
MODEL_CONFIG_PATH = os.path.join(AASIST_DIR, "config", "AASIST.conf")

SAMPLE_RATE = 16000
AUDIO_CHUNK_SAMPLES = 64600  # AASIST requirement
ROLLING_WINDOW_SECONDS = 4.0375  # exactly 64600 / 16000
UPDATE_INTERVAL_SECONDS = 2.0  # how often to run inference

# VAD config
VAD_MODE = 1  # 0 to 3
VAD_FRAME_DURATION_MS = 30  # WebRTCVAD only accepts 10, 20, 30

# Detection Config
DETECTION_THRESHOLD = float(os.environ.get("DETECTION_THRESHOLD", 0.5))
SMOOTHING_WINDOW = int(os.environ.get("SMOOTHING_WINDOW", 5))  # how many past predictions to smooth

# State Machine Thresholds
STATE_SAFE = "SAFE"
STATE_SUSPICIOUS = "SUSPICIOUS"
STATE_HIGH_RISK = "HIGH_RISK"

# If smoothed score <= SUSPICIOUS_THRESHOLD, state becomes SUSPICIOUS
SUSPICIOUS_THRESHOLD = float(os.environ.get("SUSPICIOUS_THRESHOLD", 0.6))
# If smoothed score <= HIGH_RISK_THRESHOLD, state becomes HIGH_RISK
HIGH_RISK_THRESHOLD = float(os.environ.get("HIGH_RISK_THRESHOLD", 0.3))

# ============================================================
# Gemini Audio Analysis Configuration
# ============================================================
# API key — NEVER expose this to the browser or log it.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# Request timeout in seconds for Gemini API calls
GEMINI_TIMEOUT_SECONDS = int(os.environ.get("GEMINI_TIMEOUT_SECONDS", 30))

# Maximum audio file size accepted by /api/predict (in MB)
MAX_AUDIO_SIZE_MB = float(os.environ.get("MAX_AUDIO_SIZE_MB", 50))

# Live Gemini Scheduling
GEMINI_LIVE_INTERVAL_SECONDS = int(os.environ.get("GEMINI_LIVE_INTERVAL_SECONDS", 12))
GEMINI_CACHE_MAX_AGE_SECONDS = int(os.environ.get("GEMINI_CACHE_MAX_AGE_SECONDS", 30))

# ============================================================
# RawNet2 Configuration
# ============================================================
RAWNET2_WEIGHTS_PATH = os.environ.get(
    "RAWNET2_WEIGHTS_PATH",
    os.path.join(AASIST_DIR, "models", "weights", "pre_trained_DF_RawNet2.pth")
)
RAWNET2_CONFIG_PATH = os.environ.get(
    "RAWNET2_CONFIG_PATH",
    os.path.join(AASIST_DIR, "config", "RawNet2_baseline.conf")
)

# ============================================================
# Evidence Fusion Weights
# Production defaults: AASIST=0.34, Gemini=0.33, RawNet2=0.33.
# Engine renormalizes dynamically when any model is unavailable.
# DO NOT change these without explicit evaluation on a large,
# held-out dataset. Current defaults are empirically stable.
# ============================================================
AASIST_WEIGHT = float(os.environ.get("AASIST_WEIGHT", 0.34))
GEMINI_WEIGHT = float(os.environ.get("GEMINI_WEIGHT", 0.33))
RAWNET2_WEIGHT = float(os.environ.get("RAWNET2_WEIGHT", 0.33))

# ============================================================
# Fusion Risk Classification Thresholds (spoof-probability based)
# These apply to the FUSION final_spoof score (0.0–1.0).
#
# Interpretation:
#   final_spoof < FUSION_LOW_RISK_THRESHOLD  → LOW RISK  (SAFE)
#   final_spoof < FUSION_HIGH_RISK_THRESHOLD → UNCERTAIN (SUSPICIOUS)
#   final_spoof >= FUSION_HIGH_RISK_THRESHOLD → HIGH RISK
#
# Configurable via environment or .env file.
# Defaults chosen to be conservative (minimize false negatives).
# ============================================================
FUSION_LOW_RISK_THRESHOLD  = float(os.environ.get("FUSION_LOW_RISK_THRESHOLD",  0.40))
FUSION_HIGH_RISK_THRESHOLD = float(os.environ.get("FUSION_HIGH_RISK_THRESHOLD", 0.70))
