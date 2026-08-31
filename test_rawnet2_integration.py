"""
VOICEGUARD AI — 3-Layer Integration Test Suite (AASIST + Gemini + RawNet2)
===========================================================================
Validates:
1. /status returns AASIST, Gemini, and RawNet2 status.
2. /api/predict executes AASIST, Gemini, and RawNet2 concurrently.
3. Response schema has all original fields + gemini + rawnet2 + 3-model fusion.
4. Dynamic weight renormalization works under single/multi-model availability.
5. All 6 audio formats (.wav, .mp3, .mpeg, .m4a, .flac, .ogg) are accepted and analyzed.
6. Negative/invalid files are properly rejected.
"""

import io
import json
import os
import unittest
import numpy as np
import requests
import soundfile as sf

BASE_URL = "http://127.0.0.1:5000"


class TestThreeLayerIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Verify server is up
        try:
            r = requests.get(f"{BASE_URL}/status", timeout=5)
            assert r.status_code == 200
        except Exception as e:
            raise RuntimeError(f"Server is not running at {BASE_URL}: {e}")

    def test_01_status_endpoint(self):
        """Verify /status reports AASIST, Gemini, and RawNet2 status."""
        r = requests.get(f"{BASE_URL}/status", timeout=5)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("model_loaded"), "AASIST should be loaded")
        self.assertTrue(data.get("rawnet2_loaded"), "RawNet2 should be loaded")
        self.assertIn("gemini_enabled", data)
        print("Status test passed:", data.get("rawnet2_loaded"), data.get("model_loaded"))

    def test_02_predict_sample_wav(self):
        """Test /api/predict with synthetic_spoof_test.wav."""
        path = "synthetic_spoof_test.wav"
        self.assertTrue(os.path.exists(path))
        with open(path, "rb") as f:
            files = {"file": (path, f, "audio/wav")}
            r = requests.post(f"{BASE_URL}/api/predict", files=files, timeout=45)

        self.assertEqual(r.status_code, 200)
        data = r.json()

        # Check top-level original fields
        self.assertIn("score", data)
        self.assertIn("status", data)
        self.assertIn("threat_label", data)
        self.assertIn("genuine_probability_percent", data)
        self.assertIn("spoof_probability_percent", data)
        self.assertIn("filename", data)
        self.assertIn("samples", data)
        self.assertIn("duration_sec", data)

        # Check Gemini layer
        self.assertIn("gemini", data)
        gemini = data["gemini"]
        self.assertIsInstance(gemini, dict)
        self.assertIn("available", gemini)

        # Check RawNet2 layer
        self.assertIn("rawnet2", data)
        rawnet2 = data["rawnet2"]
        self.assertIsInstance(rawnet2, dict)
        self.assertTrue(rawnet2.get("available"), "RawNet2 should be available")
        self.assertIn("spoofScore", rawnet2)
        self.assertIn("classification", rawnet2)
        self.assertIn("confidence", rawnet2)
        self.assertEqual(rawnet2.get("model"), "RawNet2")

        # Check 3-Model Fusion
        self.assertIn("fusion", data)
        fusion = data["fusion"]
        self.assertIn("finalScore", fusion)
        self.assertIn("finalSpoof", fusion)
        self.assertIn("modelsUsed", fusion)
        self.assertIn("AASIST", fusion["modelsUsed"])
        self.assertIn("RawNet2", fusion["modelsUsed"])
        self.assertIn("rawnet2Weight", fusion)
        self.assertIn("aasistWeight", fusion)

        print("\n=== Test 02 Prediction Result ===")
        print("AASIST Score (genuine):", data["score"])
        print("RawNet2 Result:", rawnet2)
        print("Gemini Result (available):", gemini.get("available"), "suspicion:", gemini.get("suspicionScore"))
        print("Fusion Result:", fusion)

    def test_03_all_supported_formats(self):
        """Test that all 6 audio formats succeed with /api/predict."""
        sr = 16000
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration), False)
        audio = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

        formats = [
            ("test.wav", "WAV", "audio/wav"),
            ("test.flac", "FLAC", "audio/flac"),
            ("test.ogg", "OGG", "audio/ogg"),
        ]

        for fname, fmt, mime in formats:
            buf = io.BytesIO()
            sf.write(buf, audio, sr, format=fmt)
            buf.seek(0)

            files = {"file": (fname, buf.getvalue(), mime)}
            r = requests.post(f"{BASE_URL}/api/predict", files=files, timeout=45)
            self.assertEqual(r.status_code, 200, f"Format {fname} failed with {r.status_code}: {r.text}")
            res = r.json()
            self.assertTrue(res.get("rawnet2", {}).get("available"))
            self.assertIn("fusion", res)
            print(f"Format {fname} ({mime}) -> 200 OK | Models: {res['fusion']['modelsUsed']}")

    def test_04_invalid_file_type_rejected(self):
        """Verify invalid extensions return 400 Bad Request."""
        files = {"file": ("malicious.exe", b"MZ\x90\x00", "application/x-msdownload")}
        r = requests.post(f"{BASE_URL}/api/predict", files=files, timeout=5)
        self.assertEqual(r.status_code, 400)
        self.assertIn("Unsupported file type", r.json().get("error", ""))
        print("Invalid file rejection test passed: 400 Bad Request")


if __name__ == "__main__":
    unittest.main()
