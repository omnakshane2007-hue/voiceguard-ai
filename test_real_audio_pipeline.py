"""
Comprehensive real audio pipeline verification test.
Tests /api/predict and /api/live_chunk on:
1. synthetic_spoof_test.wav
2. human_libri1_male.wav
3. dummy.wav
4. whatsapp_test_audio.mpeg
"""
import io
import json
import os
import sys
import numpy as np
import librosa

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app import app

client = app.test_client()

files_to_test = [
    ("synthetic_spoof_test.wav", "audio/wav", "SPOOF / SYNTHETIC"),
    ("human_libri1_male.wav", "audio/wav", "GENUINE / HUMAN"),
    ("dummy.wav", "audio/wav", "DUMMY SYNTHETIC"),
    ("whatsapp_test_audio.mpeg", "audio/mpeg", "WHATSAPP MPEG")
]

print("=" * 80)
print("VOICEGUARD AI — REAL FILE PIPELINE VERIFICATION")
print("=" * 80)

for filename, mime_type, label in files_to_test:
    if not os.path.exists(filename):
        print(f"\n[SKIP] File {filename} not found.")
        continue

    print(f"\n" + "-" * 70)
    print(f"TESTING FILE: {filename} ({label})")
    print("-" * 70)

    # 1. Test standalone librosa MPEG/WAV decode
    try:
        y, sr = librosa.load(filename, sr=16000, mono=True)
        print(f"[1. Audio Decode] SUCCESS: samples={len(y)}, duration={len(y)/sr:.2f}s, max_amp={np.max(np.abs(y)):.4f}")
    except Exception as e:
        print(f"[1. Audio Decode] FAILED: {e}")
        continue

    # 2. Test /api/predict
    with open(filename, 'rb') as f:
        file_bytes = f.read()

    data = {'file': (io.BytesIO(file_bytes), filename, mime_type)}
    res_predict = client.post('/api/predict', data=data, content_type='multipart/form-data')
    print(f"[2. /api/predict] HTTP Status: {res_predict.status_code}")
    try:
        pred_json = res_predict.get_json()
        if res_predict.status_code == 200:
            print(f"    - Score (Genuine %): {pred_json.get('genuine_probability_percent')}%")
            print(f"    - Status: {pred_json.get('status')} ({pred_json.get('threat_label')})")
            print(f"    - RawNet2 Available: {pred_json.get('rawnet2', {}).get('available')} (SpoofScore: {pred_json.get('rawnet2', {}).get('spoofScore')})")
            print(f"    - Gemini Available: {pred_json.get('gemini', {}).get('available')}")
            print(f"    - Fusion Models Used: {pred_json.get('fusion', {}).get('modelsUsed')}")
            print(f"    - Fusion Final Spoof: {pred_json.get('fusion', {}).get('finalSpoof')}")
            print(f"    - Fusion Classification: {pred_json.get('fusion', {}).get('classification')}")
            print(f"    - Model Disagreement: {pred_json.get('fusion', {}).get('modelDisagreement')}")
        else:
            print(f"    - Error payload: {json.dumps(pred_json, indent=2)}")
    except Exception as e:
        print(f"    - JSON parse error: {e}")

    # 3. Test /api/live_chunk with first 4 seconds (~64600 samples)
    chunk_samples = y[:min(len(y), 64600)]
    buf_chunk = io.BytesIO()
    import soundfile as sf
    sf.write(buf_chunk, chunk_samples, 16000, format='WAV')
    chunk_bytes = buf_chunk.getvalue()

    chunk_data = {'file': (io.BytesIO(chunk_bytes), 'live_chunk.wav', 'audio/wav')}
    res_live = client.post('/api/live_chunk', data=chunk_data, content_type='multipart/form-data')
    print(f"[3. /api/live_chunk] HTTP Status: {res_live.status_code}")
    try:
        live_json = res_live.get_json()
        if res_live.status_code == 200:
            print(f"    - Speech Detected: {live_json.get('speechDetected')}, Speech Ratio: {live_json.get('speechRatio')}")
            print(f"    - State: {live_json.get('state')}, Fusion Score: {live_json.get('fusionScore')}")
            print(f"    - Latency: {live_json.get('processingTimeMs')}ms")
            print(f"    - Models: {live_json.get('models')}")
        else:
            print(f"    - Error payload: {json.dumps(live_json, indent=2)}")
    except Exception as e:
        print(f"    - JSON parse error: {e}")

print("\n" + "=" * 80)
print("ALL REAL FILE PIPELINE TESTS COMPLETE")
print("=" * 80)
