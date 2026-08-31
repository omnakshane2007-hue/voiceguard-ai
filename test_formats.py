"""
VOICEGUARD AI - Audio Formats Test Suite
Tests: .wav, .mp3, .mpeg, .m4a, .flac, .ogg + rejection of invalid formats
"""
import io
import os
import sys
import numpy as np
import requests
import soundfile as sf

BASE = "http://localhost:5000"

print("=" * 65)
print("VOICEGUARD AI — Comprehensive Audio Formats Test Suite")
print("=" * 65)

# Generate a 3-second 440Hz test audio signal
sr = 16000
duration = 3.0
t = np.linspace(0, duration, int(sr * duration), endpoint=False)
audio_data = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

# Create buffers for various formats
wav_bytes = io.BytesIO()
sf.write(wav_bytes, audio_data, sr, format='WAV')
wav_bytes = wav_bytes.getvalue()

flac_bytes = io.BytesIO()
sf.write(flac_bytes, audio_data, sr, format='FLAC')
flac_bytes = flac_bytes.getvalue()

ogg_bytes = io.BytesIO()
sf.write(ogg_bytes, audio_data, sr, format='OGG')
ogg_bytes = ogg_bytes.getvalue()

mp3_bytes = io.BytesIO()
sf.write(mp3_bytes, audio_data, sr, format='MP3')
mp3_bytes = mp3_bytes.getvalue()

# Test matrix: (format_name, filename, bytes, mime_type, should_succeed)
test_cases = [
    # Supported formats
    ("WAV format (.wav)", "test_sample.wav", wav_bytes, "audio/wav", True),
    ("MP3 format (.mp3)", "test_sample.mp3", mp3_bytes, "audio/mpeg", True),
    ("MPEG format (.mpeg)", "test_sample.mpeg", mp3_bytes, "audio/mpeg", True),
    ("M4A format (.m4a)", "test_sample.m4a", mp3_bytes, "audio/mp4", True),
    ("FLAC format (.flac)", "test_sample.flac", flac_bytes, "audio/flac", True),
    ("OGG format (.ogg)", "test_sample.ogg", ogg_bytes, "audio/ogg", True),
    
    # Invalid formats (must be rejected)
    ("Executable (.exe)", "malware.exe", b"MZ_FAKE_BINARY_DATA", "application/octet-stream", False),
    ("Text file (.txt)", "notes.txt", b"plain text data", "text/plain", False),
    ("PDF document (.pdf)", "doc.pdf", b"%PDF-1.4...", "application/pdf", False),
]

passed_count = 0
failed_count = 0

for desc, filename, data_bytes, mime, should_succeed in test_cases:
    print(f"\n[TEST] {desc} -> filename: '{filename}'")
    try:
        r = requests.post(
            f"{BASE}/api/predict",
            files={"file": (filename, io.BytesIO(data_bytes), mime)},
            timeout=60
        )
        res = r.json()

        if should_succeed:
            if r.status_code == 200:
                score = res.get("score")
                status = res.get("status")
                g_avail = res.get("gemini", {}).get("available")
                f_score = res.get("fusion", {}).get("finalScore")
                print(f"  [PASS] HTTP 200 | AASIST Score: {score:.4f} | Status: {status}")
                print(f"         Gemini available: {g_avail} | Fusion Score: {f_score}")
                passed_count += 1
            else:
                print(f"  [FAIL] Expected 200, got {r.status_code}: {res.get('error')}")
                failed_count += 1
        else:
            if r.status_code == 400:
                err = res.get("error", "")
                print(f"  [PASS] Correctly rejected with HTTP 400: '{err}'")
                passed_count += 1
            else:
                print(f"  [FAIL] Expected 400 rejection, got {r.status_code}: {res}")
                failed_count += 1

    except Exception as e:
        print(f"  [ERROR] {e}")
        failed_count += 1

print("\n" + "=" * 65)
print(f"RESULTS: {passed_count} PASSED / {passed_count + failed_count} TOTAL")
print("=" * 65)

if failed_count > 0:
    sys.exit(1)
else:
    print("ALL FORMAT TESTS PASSED SUCCESSFULLY!")
