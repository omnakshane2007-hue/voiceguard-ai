from __future__ import annotations

"""
VOICEGUARD AI — RawNet2 Audio Anti-Spoofing Analyzer
=====================================================
Dedicated deep learning anti-spoofing layer using RawNet2.
Evaluates raw waveforms (16 kHz, 64,600 samples) to detect synthetic/cloned speech.

Architecture & Citation:
    Hemlata Tak, Jose Patino, Andreas Nautsch, Nicholas Evans.
    "End-to-end anti-spoofing with RawNet2"
    ICASSP 2021 / ASVspoof Baseline

Score Semantics:
    Model outputs logsoftmax over 2 classes:
        Class 0 = Spoof / Synthetic
        Class 1 = Bonafide / Genuine
    We extract:
        genuine_prob = exp(logsoftmax)[:, 1]   (range: [0.0, 1.0])
        spoof_score  = 1.0 - genuine_prob       (range: [0.0, 1.0])
            0.0 = completely authentic
            1.0 = completely synthetic / spoofed

Normalization & Thresholds:
    spoof_score >= 0.60 -> "SYNTHETIC"
    spoof_score >= 0.40 -> "UNCERTAIN"
    else                -> "AUTHENTIC"
"""

import io
import json
import logging
import os
import sys
import tempfile
import time
from typing import Any

import librosa
import numpy as np
try:
    import torch
    import torch.nn.functional as F
except ImportError:
    torch = None
    F = None

import config

logger = logging.getLogger(__name__)

# Default model configuration for RawNet2 ASVspoof 2019/2021 architecture
DEFAULT_RAWNET2_CONFIG = {
    "architecture": "RawNet2Spoof",
    "nb_samp": 64600,
    "first_conv": 1024,
    "in_channels": 1,
    "filts": [20, [20, 20], [20, 128], [128, 128]],
    "blocks": [2, 4],
    "nb_fc_node": 1024,
    "gru_node": 1024,
    "nb_gru_layer": 3,
    "nb_classes": 2,
}


def _make_unavailable_result(reason: str) -> dict[str, Any]:
    """Helper to construct a standardized 'model unavailable' response."""
    return {
        "available": False,
        "classification": "UNAVAILABLE",
        "spoofScore": None,
        "genuineScore": None,
        "confidence": None,
        "model": "RawNet2",
        "error": reason,
    }


class RawNet2Analyzer:
    """
    Manages RawNet2 model loading and audio inference.
    Is isolated from AASIST and Gemini services.
    """

    def __init__(
        self,
        weights_path: str | None = None,
        config_path: str | None = None,
    ):
        self.weights_path = weights_path or config.RAWNET2_WEIGHTS_PATH
        self.config_path = config_path or config.RAWNET2_CONFIG_PATH
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu") if torch is not None else "cpu"
        self.model = None
        self._is_loaded = False
        self._load_error: str | None = None

        # Attempt eager load on startup
        self.load_model()

    def load_model(self) -> bool:
        """
        Load the RawNet2 model architecture and pre-trained weights.
        Returns True if successful, False otherwise.
        """
        if self._is_loaded and self.model is not None:
            return True

        if torch is None:
            self._load_error = "PyTorch is unavailable in this environment."
            logger.warning("[RawNet2] %s", self._load_error)
            return False

        logger.info("[RawNet2] Initializing model on device: %s", self.device)

        # Ensure aasist directory is on sys.path to import RawNet2 architecture
        if config.AASIST_DIR not in sys.path:
            sys.path.append(config.AASIST_DIR)

        try:
            from models.RawNet2Spoof import Model as RawNet2Model
        except ImportError as exc:
            self._load_error = f"Failed to import RawNet2Spoof model: {exc}"
            logger.error("[RawNet2] %s", self._load_error)
            return False

        # Load architecture configuration
        model_cfg = DEFAULT_RAWNET2_CONFIG
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    conf_data = json.load(f)
                    model_cfg = conf_data.get("model_config", DEFAULT_RAWNET2_CONFIG)
            except Exception as exc:
                logger.warning("[RawNet2] Could not parse config at %s, using defaults: %s", self.config_path, exc)

        # Check weights file
        if not os.path.exists(self.weights_path):
            self._load_error = f"RawNet2 weights file not found at {self.weights_path}"
            logger.warning("[RawNet2] %s", self._load_error)
            return False

        try:
            model = RawNet2Model(model_cfg).to(self.device)
            state_dict = torch.load(self.weights_path, map_location=self.device)
            model.load_state_dict(state_dict)
            model.eval()

            self.model = model
            self._is_loaded = True
            self._load_error = None
            logger.info("[RawNet2] Pre-trained weights loaded successfully from: %s", self.weights_path)
            return True
        except Exception as exc:
            self._load_error = f"Failed to load RawNet2 weights: {exc}"
            logger.error("[RawNet2] %s", self._load_error, exc_info=True)
            self.model = None
            self._is_loaded = False
            return False

    def is_available(self) -> bool:
        """Returns True if the RawNet2 model is loaded and ready for inference."""
        return self._is_loaded and self.model is not None

    def analyze(self, audio_bytes: bytes, filename: str = "audio.wav") -> dict[str, Any]:
        """
        Analyze audio bytes with RawNet2.

        Parameters:
            audio_bytes: Raw audio binary data
            filename: Original file name (used for extension detection in container formats)

        Returns:
            dict containing:
                available: bool
                classification: "AUTHENTIC" | "SYNTHETIC" | "UNCERTAIN"
                spoofScore: float [0.0 - 1.0] (0 = authentic, 1 = synthetic)
                genuineScore: float [0.0 - 1.0]
                confidence: float [0 - 100]
                model: "RawNet2"
                error: str | None
        """
        if not self.is_available():
            # Try reloading once in case weights appeared
            if not self.load_model():
                return _make_unavailable_result(self._load_error or "RawNet2 model is not loaded")

        if not audio_bytes or len(audio_bytes) == 0:
            return _make_unavailable_result("Empty audio data received")

        t0 = time.monotonic()

        try:
            # Preprocess audio to 16 kHz, 64,600-sample tensor
            audio_tensor = self._preprocess_audio(audio_bytes, filename)
        except Exception as exc:
            logger.warning("[RawNet2] Preprocessing failed: %s", exc)
            return _make_unavailable_result(f"Preprocessing error: {exc}")

        # Run model forward pass
        try:
            with torch.no_grad():
                audio_tensor = audio_tensor.to(self.device)
                _, output = self.model(audio_tensor)
                
                # Output is logsoftmax: shape (1, 2)
                # Class 0 = Spoof, Class 1 = Bonafide
                probs = torch.exp(output)[0]
                spoof_prob = float(probs[0].item())
                genuine_prob = float(probs[1].item())

                # Clamp scores to [0.0, 1.0]
                spoof_score = max(0.0, min(1.0, spoof_prob))
                genuine_score = max(0.0, min(1.0, genuine_prob))

                # Determine classification label
                if spoof_score >= 0.60:
                    classification = "SYNTHETIC"
                elif spoof_score >= 0.40:
                    classification = "UNCERTAIN"
                else:
                    classification = "AUTHENTIC"

                # Confidence: distance from uncertainty midpoint (0.50) scaled to 0-100
                confidence = round(min(100.0, abs(spoof_score - 0.5) * 200), 1)

                duration_ms = (time.monotonic() - t0) * 1000
                logger.info(
                    "[RawNet2] Inference complete in %.1fms: spoof=%.4f genuine=%.4f (%s)",
                    duration_ms, spoof_score, genuine_score, classification
                )

                return {
                    "available": True,
                    "classification": classification,
                    "spoofScore": round(spoof_score, 4),
                    "genuineScore": round(genuine_score, 4),
                    "confidence": confidence,
                    "model": "RawNet2",
                    "error": None,
                }

        except Exception as exc:
            logger.error("[RawNet2] Inference error: %s", exc, exc_info=True)
            return _make_unavailable_result(f"Inference failed: {exc}")

    def _preprocess_audio(self, audio_bytes: bytes, filename: str) -> Any:
        """
        Decode audio bytes into a 16 kHz mono waveform and standardize to 64,600 samples.
        """
        # Try direct in-memory load
        try:
            y, sr = librosa.load(io.BytesIO(audio_bytes), sr=config.SAMPLE_RATE, mono=True)
        except Exception:
            # Fallback to temp file for container formats (e.g. m4a, ogg)
            ext = os.path.splitext(filename)[1].lower() or ".wav"
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            try:
                y, sr = librosa.load(tmp_path, sr=config.SAMPLE_RATE, mono=True)
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

        if len(y) == 0 or np.max(np.abs(y)) < 0.0001:
            raise ValueError("Audio file appears to be empty or pure silence.")

        target_len = config.AUDIO_CHUNK_SAMPLES  # 64,600 samples

        if len(y) >= target_len:
            y_processed = y[:target_len]
        else:
            num_repeats = int(target_len / len(y)) + 1
            y_processed = np.tile(y, num_repeats)[:target_len]

        # Return tensor with shape (1, 64600)
        return torch.tensor(y_processed, dtype=torch.float32).unsqueeze(0)
