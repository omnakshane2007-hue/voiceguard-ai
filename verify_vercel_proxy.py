"""
Verify Vercel public frontend deployment end-to-end through Vercel rewrites to Railway.
"""
import requests
import json
import os

VERCEL_URLS = [
    "https://voiceguardai-delta.vercel.app",
    "https://voiceguardai-hz5xmplou-omnakshane53-4370s-projects.vercel.app"
]

for base_url in VERCEL_URLS:
    print("\n" + "=" * 80)
    print(f"TESTING VERCEL DOMAIN: {base_url}")
    print("=" * 80)

    # 1. GET /
    try:
        r_root = requests.get(f"{base_url}/", timeout=15)
        print(f"[1. GET /] HTTP {r_root.status_code} (length: {len(r_root.text)} bytes)")
    except Exception as e:
        print(f"[1. GET /] ERROR: {e}")

    # 2. GET /status (proxied to Railway)
    try:
        r_status = requests.get(f"{base_url}/status", timeout=15)
        print(f"[2. GET /status] HTTP {r_status.status_code}")
        print("   Payload:", json.dumps(r_status.json(), indent=2))
    except Exception as e:
        print(f"[2. GET /status] ERROR: {e}")

    # 3. GET /health (proxied to Railway)
    try:
        r_health = requests.get(f"{base_url}/health", timeout=15)
        print(f"[3. GET /health] HTTP {r_health.status_code}")
        print("   Payload:", json.dumps(r_health.json(), indent=2))
    except Exception as e:
        print(f"[3. GET /health] ERROR: {e}")

    # 4. POST /api/predict with synthetic_spoof_test.wav (proxied to Railway)
    try:
        with open("synthetic_spoof_test.wav", "rb") as f:
            r_wav = requests.post(
                f"{base_url}/api/predict",
                files={"file": ("synthetic_spoof_test.wav", f, "audio/wav")},
                timeout=45
            )
        print(f"[4. POST /api/predict WAV] HTTP {r_wav.status_code}")
        wav_json = r_wav.json()
        print(f"   score: {wav_json.get('score')}")
        print(f"   genuine_probability_percent: {wav_json.get('genuine_probability_percent')}%")
        print(f"   spoof_probability_percent: {wav_json.get('spoof_probability_percent')}%")
        print(f"   status: {wav_json.get('status')} ({wav_json.get('threat_label')})")
        print(f"   fusion: {json.dumps(wav_json.get('fusion'), indent=2)}")
    except Exception as e:
        print(f"[4. POST /api/predict WAV] ERROR: {e}")

    # 5. POST /api/predict with whatsapp_test_audio.mpeg (proxied to Railway)
    try:
        with open("whatsapp_test_audio.mpeg", "rb") as f:
            r_mpeg = requests.post(
                f"{base_url}/api/predict",
                files={"file": ("whatsapp_test_audio.mpeg", f, "audio/mpeg")},
                timeout=45
            )
        print(f"[5. POST /api/predict MPEG] HTTP {r_mpeg.status_code}")
        mpeg_json = r_mpeg.json()
        print(f"   score: {mpeg_json.get('score')}")
        print(f"   genuine_probability_percent: {mpeg_json.get('genuine_probability_percent')}%")
        print(f"   spoof_probability_percent: {mpeg_json.get('spoof_probability_percent')}%")
        print(f"   status: {mpeg_json.get('status')} ({mpeg_json.get('threat_label')})")
        print(f"   fusion: {json.dumps(mpeg_json.get('fusion'), indent=2)}")
    except Exception as e:
        print(f"[5. POST /api/predict MPEG] ERROR: {e}")

    # 6. POST /api/live_chunk (proxied to Railway)
    try:
        with open("synthetic_spoof_test.wav", "rb") as f:
            chunk_bytes = f.read()[:64600 * 2]
        r_live = requests.post(
            f"{base_url}/api/live_chunk",
            files={"file": ("live_chunk.wav", chunk_bytes, "audio/wav")},
            timeout=30
        )
        print(f"[6. POST /api/live_chunk] HTTP {r_live.status_code}")
        live_json = r_live.json()
        print(f"   state: {live_json.get('state')}")
        print(f"   fusionScore: {live_json.get('fusionScore')}")
        print(f"   smoothedScore: {live_json.get('smoothedScore')}")
        print(f"   geminiScore: {live_json.get('geminiScore')} (status: {live_json.get('geminiStatus')})")
        print(f"   models: {live_json.get('models')}")
        print(f"   processingTimeMs: {live_json.get('processingTimeMs')}ms")
    except Exception as e:
        print(f"[6. POST /api/live_chunk] ERROR: {e}")
