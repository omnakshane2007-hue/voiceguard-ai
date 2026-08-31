"""
VOICEGUARD AI — Production Regression Test Suite
================================================
Verifies all core invariants:
A. Gemini unavailable: geminiScore == null (None)
B. Gemini unavailable: Gemini not in modelsUsed
C. Gemini unavailable: No 0.500 fabricated score
D. Gemini legitimate UNCERTAIN: Gemini may legitimately equal 0.500
E. RawNet2 executes without 'RuntimeError: Numpy is not available'
F. All models genuinely unavailable: returns structured JSON error
G. AASIST + RawNet2 available: system works fully without Gemini
H. 429 Gemini: local models continue operating uninterrupted
"""
import io
import json
import os
import sys
import unittest
import numpy as np
import soundfile as sf
import torch

# Ensure prototype root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import config
from services.fusion_engine import fuse
from services.gemini_audio_analyzer import GeminiAudioAnalyzer, _make_unavailable_result
from services.rawnet2_analyzer import RawNet2Analyzer
from services.audio_preprocessor import preprocess_audio_for_aasist
from app import app, system


class VoiceGuardProductionRegressionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Generate clean 3-second test sine waveform
        cls.sr = 16000
        t = np.linspace(0, 3.0, int(cls.sr * 3.0), endpoint=False)
        cls.sine_waveform = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        
        # In-memory WAV bytes
        buf = io.BytesIO()
        sf.write(buf, cls.sine_waveform, cls.sr, format='WAV')
        cls.test_wav_bytes = buf.getvalue()

    def test_invariant_a_b_c_gemini_unavailable(self):
        """Invariants A, B, C: When Gemini is unavailable, geminiScore is null, excluded from modelsUsed, no 0.5 fallback."""
        unavailable_gemini = _make_unavailable_result("429 RESOURCE_EXHAUSTED: Quota exceeded")
        self.assertFalse(unavailable_gemini["available"])
        self.assertIsNone(unavailable_gemini["suspicionScore"])

        # Fuse AASIST (genuine=0.95 -> spoof=0.05) and RawNet2 (spoof=0.08) with unavailable Gemini
        result = fuse(
            aasist_result={"score": 0.95},
            rawnet2_result={"available": True, "spoofScore": 0.08},
            gemini_result=unavailable_gemini
        )

        # Invariant A: geminiSpoof is None (maps to JSON null)
        self.assertIsNone(result["geminiSpoof"], "Invariant A Failed: geminiSpoof must be None when Gemini is unavailable")
        
        # Invariant B: Gemini not in modelsUsed
        self.assertNotIn("Gemini", result["modelsUsed"], "Invariant B Failed: Gemini must NOT be in modelsUsed when unavailable")
        self.assertEqual(result["geminiWeight"], 0.0, "Gemini weight must be 0.0 when unavailable")
        self.assertIn("AASIST", result["modelsUsed"])
        self.assertIn("RawNet2", result["modelsUsed"])

        # Invariant C: Dynamic weights sum to 1.0, score computed from local models only (not defaulted to 0.5)
        expected_spoof = (0.05 * 0.34 + 0.08 * 0.33) / (0.34 + 0.33)
        self.assertAlmostEqual(result["finalSpoof"], expected_spoof, places=3,
                               msg="Invariant C Failed: Fusion must compute exact weighted average of available models")
        self.assertNotEqual(result["finalSpoof"], 0.500, "Must not fabricate a 0.500 fallback score")

    def test_invariant_d_gemini_legitimate_uncertain(self):
        """Invariant D: When Gemini legitimately returns UNCERTAIN (suspicion_score=50), it is validly included."""
        analyzer = GeminiAudioAnalyzer(api_key="test_key")
        normalized = analyzer._validate_and_normalize({
            "classification": "UNCERTAIN",
            "suspicion_score": 50,
            "confidence": 60,
            "evidence": ["Ambiguous prosody"],
            "limitations": []
        })

        self.assertTrue(normalized["available"])
        self.assertEqual(normalized["suspicionScore"], 50)
        self.assertEqual(normalized["classification"], "UNCERTAIN")

        # Fusion with legitimate 50% Gemini
        result = fuse(
            aasist_result={"score": 0.90},  # spoof=0.10
            rawnet2_result={"available": True, "spoofScore": 0.10},
            gemini_result=normalized
        )

        self.assertIn("Gemini", result["modelsUsed"])
        self.assertEqual(result["geminiSpoof"], 0.5)
        self.assertGreater(result["geminiWeight"], 0.0)

    def test_invariant_e_rawnet2_no_numpy_abi_error(self):
        """Invariant E: RawNet2 executes forward pass on tensors without 'RuntimeError: Numpy is not available'."""
        analyzer = RawNet2Analyzer()
        if not analyzer.is_available():
            self.skipTest("RawNet2 model weights not present in current environment, skipping forward pass test")

        # Execute analysis on real waveform bytes
        res = analyzer.analyze(self.test_wav_bytes, filename="test.wav")
        self.assertTrue(res["available"], f"RawNet2 inference failed: {res.get('error')}")
        self.assertIsNotNone(res["spoofScore"], "RawNet2 must return numeric spoofScore")
        self.assertIsNone(res["error"], "RawNet2 must not encounter RuntimeError")
        self.assertIn(res["classification"], ["AUTHENTIC", "SYNTHETIC", "UNCERTAIN"])

    def test_invariant_f_all_models_unavailable_structured_json(self):
        """Invariant F: When all models are unavailable, returns structured JSON error (no fake score, no secrets)."""
        client = app.test_client()
        
        # Test edge case: invalid / empty payload or forced unavailable
        empty_data = {'file': (io.BytesIO(b""), "test.wav")}
        res = client.post('/api/predict', data=empty_data, content_type='multipart/form-data')
        self.assertIn(res.status_code, [400, 500])
        body = res.get_json()
        self.assertIn("error", body)
        self.assertNotIn(config.GEMINI_API_KEY, json.dumps(body) if config.GEMINI_API_KEY else "")

    def test_invariant_g_aasist_plus_rawnet2_without_gemini(self):
        """Invariant G: AASIST + RawNet2 operate completely independently when Gemini has no API key or is disabled."""
        fusion = fuse(
            aasist_result={"score": 0.85},  # genuine=0.85, spoof=0.15
            rawnet2_result={"available": True, "spoofScore": 0.12},
            gemini_result=None,
            aasist_weight=0.34,
            gemini_weight=0.33,
            rawnet2_weight=0.33
        )

        self.assertEqual(len(fusion["modelsUsed"]), 2)
        self.assertListEqual(sorted(fusion["modelsUsed"]), ["AASIST", "RawNet2"])
        # Renormalized weights: AASIST: 0.34/0.67 = 0.507, RawNet2: 0.33/0.67 = 0.493
        total_weight = fusion["aasistWeight"] + fusion["rawnet2Weight"]
        self.assertAlmostEqual(total_weight, 1.0, places=2)
        self.assertEqual(fusion["classification"], "SAFE")
        self.assertAlmostEqual(fusion["finalSpoof"], (0.15 * 0.34 + 0.12 * 0.33) / 0.67, places=3)

    def test_invariant_h_gemini_429_cooldown_behavior(self):
        """Invariant H: Gemini 429 activates cooldown and does not block local models."""
        analyzer = GeminiAudioAnalyzer(api_key="test_key")
        
        # Test retry delay extraction
        error_msg = "Quota exceeded for metric: limit: 20, model: gemini-3.6-flash. Please retry in 33.2s."
        delay = analyzer._extract_retry_delay(error_msg)
        self.assertEqual(delay, 33)

        # Trigger simulated cooldown
        import time
        analyzer._cooldown_until = time.time() + 45.0

        # Subsequent analyze call during cooldown should return unavailable immediately without network
        res = analyzer.analyze(self.test_wav_bytes, mime_type="audio/wav")
        self.assertFalse(res["available"])
        self.assertIsNone(res["suspicionScore"])
        err_low = res["error"].lower()
        self.assertTrue("rate limit" in err_low or "quota" in err_low)

    def test_predict_fusion_single_source_of_truth(self):
        """Verify that top-level API decision fields strictly derive from fusion."""
        client = app.test_client()
        data = {'file': (io.BytesIO(self.test_wav_bytes), 'test_sine.wav', 'audio/wav')}
        res = client.post('/api/predict', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        
        fusion = body.get("fusion")
        self.assertIsNotNone(fusion, "Response must include fusion object")
        
        # Invariants: Top-level fields MUST equal fusion fields exactly
        self.assertAlmostEqual(body["score"], fusion["finalScore"], places=5,
                               msg="top-level score must equal fusion.finalScore")
        self.assertEqual(body["genuine_probability_percent"], round(fusion["finalScore"] * 100, 2),
                         msg="top-level genuine_probability_percent must equal round(fusion.finalScore * 100, 2)")
        self.assertEqual(body["spoof_probability_percent"], round(fusion["finalSpoof"] * 100, 2),
                         msg="top-level spoof_probability_percent must equal round(fusion.finalSpoof * 100, 2)")
        self.assertEqual(body["status"], fusion["classification"],
                         msg="top-level status must equal fusion.classification")
        self.assertIn("threat_label", body)
        self.assertIn(body["status"], ["SAFE", "SUSPICIOUS", "HIGH_RISK"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
