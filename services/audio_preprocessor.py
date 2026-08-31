"""
VOICEGUARD AI — Audio Preprocessing Utilities
=============================================
Speech-preserving preprocessing for anti-spoofing deep learning models (AASIST & RawNet2).

Key Principles:
1. Safe Padding: Uses np.tile() for short audio to preserve continuous energy, similar to RawNet2.
2. Minimal Trimming: Relies on application-level VAD instead of destructive librosa.trim.
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
) -> np.ndarray:
    """
    Preprocesses raw audio waveform for AASIST inference.

    Parameters:
        y: 1D numpy array of audio samples (assumed 16 kHz mono).
        max_len: Required sample count (default 64,600).

    Returns:
        1D float32 numpy array of shape (max_len,).

    Raises:
        ValueError: If audio is empty, None, or below minimum amplitude threshold.
    """
    if y is None or len(y) == 0 or float(np.max(np.abs(y))) < 0.0001:
        raise ValueError("Audio file appears to be empty or pure silence.")

    y = np.asarray(y, dtype=np.float32)

    # 1. Skip aggressive librosa.effects.trim. Live audio is already VAD-filtered.
    # We rely on the natural microphone envelope to avoid abrupt artificial digital silence.
    y_use = y

    # 2. Skip forced target_peak normalization (0.40) which was distorting dynamics
    # and amplifying noise. Instead, we only normalize if it clips (> 1.0)
    current_peak = float(np.max(np.abs(y_use)))
    if current_peak > 1.0:
        y_use = y_use / current_peak

    n_samples = len(y_use)

    # 3. Extract 64,600 samples of active speech or tile to preserve continuous energy
    if n_samples >= max_len:
        y_processed = y_use[:max_len]
    else:
        # Tiling is much safer for AASIST than appending 2-3 seconds of pure digital zeros,
        # which SincNet heavily penalizes as synthetic gating artifacts.
        num_repeats = int(max_len / n_samples) + 1
        y_processed = np.tile(y_use, num_repeats)[:max_len]

    return y_processed.astype(np.float32)

