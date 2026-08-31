"""
VOICEGUARD AI — Audio Preprocessing Utilities
=============================================
Speech-preserving preprocessing for anti-spoofing deep learning models (AASIST & RawNet2).

Key Principles:
1. Safe Zero-Padding: Eliminates artificial boundary clicks and spectral comb filters
   caused by np.tile() on short audio (< 64,600 samples).
2. Silence Trimming: Uses energy-based voice activity trimming to remove leading and
   trailing dead air so the models evaluate active speech rather than room silence.
3. Fixed Dimension: Outputs exactly 64,600 samples (4.0375s @ 16 kHz mono float32).
4. Strict Validation: Rejects empty or purely silent audio with ValueError.
"""

import logging
import librosa
import numpy as np

import config

logger = logging.getLogger(__name__)


def preprocess_audio_for_aasist(
    y: np.ndarray,
    max_len: int = config.AUDIO_CHUNK_SAMPLES,
    target_peak: float = 0.40,
    top_db: int = 40
) -> np.ndarray:
    """
    Preprocesses raw audio waveform for AASIST inference.

    Parameters:
        y: 1D numpy array of audio samples (assumed 16 kHz mono).
        max_len: Required sample count (default 64,600).
        target_peak: Target peak amplitude scaling (default 0.40) ensuring waveform
                     activations match AASIST SincNet training domain (prevents saturation
                     and false-positives on mobile AGC / WhatsApp compressed audio).
        top_db: Decibel threshold below peak for silence trimming (default 40 dB).

    Returns:
        1D float32 numpy array of shape (max_len,).

    Raises:
        ValueError: If audio is empty, None, or below minimum amplitude threshold.
    """
    if y is None or len(y) == 0 or float(np.max(np.abs(y))) < 0.0001:
        raise ValueError("Audio file appears to be empty or pure silence.")

    y = np.asarray(y, dtype=np.float32)

    # 1. Gentle silence trimming (top_db=40 preserves all speech onsets and transitions)
    try:
        y_trimmed, _ = librosa.effects.trim(
            y,
            top_db=top_db,
            frame_length=1024,
            hop_length=256
        )
        # Use trimmed audio if at least 0.25s (4000 samples) remain; else retain y
        if len(y_trimmed) >= 4000:
            y_use = y_trimmed
        else:
            y_use = y
    except Exception as exc:
        logger.debug("[Preprocessor] Silence trimming fallback: %s", exc)
        y_use = y

    # 2. Dynamic range scaling to AASIST receptive field
    current_peak = float(np.max(np.abs(y_use)))
    if current_peak > 0:
        y_use = y_use * (target_peak / current_peak)

    n_samples = len(y_use)

    # 3. Extract 64,600 samples of active speech or safe zero-pad
    if n_samples >= max_len:
        y_processed = y_use[:max_len]
    else:
        # Safe zero-padding on the right (NO periodic np.tile)
        y_processed = np.pad(
            y_use,
            (0, max_len - n_samples),
            mode="constant",
            constant_values=0.0
        )

    return y_processed.astype(np.float32)
