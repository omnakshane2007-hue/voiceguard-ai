"""
Verify live Railway deployment status and test live /api/predict endpoints.
"""
import requests
import time
import json
import sys

RAILWAY_URL = "https://voiceguard-ai-production.up.railway.app"
print(f"Connecting to Railway deployment at {RAILWAY_URL}...")

max_attempts = 24  # Poll for up to ~2 minutes
status_ok = False

for attempt in range(1, max_attempts + 1):
    try:
        r = requests.get(f"{RAILWAY_URL}/status", timeout=10)
        if r.status_code == 200:
            data = r.json()
            models_health = data.get("models_health", {})
            aasist = models_health.get("AASIST")
            rawnet2 = models_health.get("RawNet2")
            gemini = models_health.get("Gemini")
            print(f"[Attempt {attempt}] Railway /status: HTTP 200")
            print(f"   AASIST: {aasist}")
            print(f"   RawNet2: {rawnet2}")
            print(f"   Gemini: {gemini}")
            print(f"   Full status payload: {json.dumps(data, indent=2)}")
            if aasist == "loaded" and rawnet2 == "loaded":
                status_ok = True
                break
        else:
            print(f"[Attempt {attempt}] HTTP {r.status_code}: {r.text[:100]}")
    except Exception as e:
        print(f"[Attempt {attempt}] Connection error: {e}")
    
    time.sleep(5)

if not status_ok:
    print("\n[WARNING] Railway service did not report fully loaded models within the polling window. Testing anyway...")

# Test 1: WAV file predict against Railway
print("\n" + "=" * 70)
print("TEST 1: Live Railway /api/predict with synthetic_spoof_test.wav")
print("=" * 70)
try:
    with open("synthetic_spoof_test.wav", "rb") as f:
        r_wav = requests.post(
            f"{RAILWAY_URL}/api/predict",
            files={"file": ("synthetic_spoof_test.wav", f, "audio/wav")},
            timeout=45
        )
    print(f"HTTP Status: {r_wav.status_code}")
    print(json.dumps(r_wav.json(), indent=2))
except Exception as e:
    print(f"WAV Test Error: {e}")

# Test 2: WhatsApp MPEG file predict against Railway
print("\n" + "=" * 70)
print("TEST 2: Live Railway /api/predict with whatsapp_test_audio.mpeg")
print("=" * 70)
try:
    with open("whatsapp_test_audio.mpeg", "rb") as f:
        r_mpeg = requests.post(
            f"{RAILWAY_URL}/api/predict",
            files={"file": ("whatsapp_test_audio.mpeg", f, "audio/mpeg")},
            timeout=45
        )
    print(f"HTTP Status: {r_mpeg.status_code}")
    print(json.dumps(r_mpeg.json(), indent=2))
except Exception as e:
    print(f"MPEG Test Error: {e}")

# Test 3: Live chunk against Railway
print("\n" + "=" * 70)
print("TEST 3: Live Railway /api/live_chunk")
print("=" * 70)
try:
    with open("synthetic_spoof_test.wav", "rb") as f:
        chunk_bytes = f.read()[:64600 * 2]
    r_live = requests.post(
        f"{RAILWAY_URL}/api/live_chunk",
        files={"file": ("live_chunk.wav", chunk_bytes, "audio/wav")},
        timeout=30
    )
    print(f"HTTP Status: {r_live.status_code}")
    print(json.dumps(r_live.json(), indent=2))
except Exception as e:
    print(f"Live Chunk Test Error: {e}")
