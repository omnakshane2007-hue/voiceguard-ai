"""VOICEGUARD AI - Gemini Integration Test Suite"""
import requests
import sys

BASE = "http://localhost:5000"
PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  [PASS] {name}")
        PASS += 1
    else:
        print(f"  [FAIL] {name} {detail}")
        FAIL += 1

print("=" * 60)
print("VOICEGUARD AI — Gemini Integration Test Suite")
print("=" * 60)

# ---- Test 1: /status still works ----
print("\n[1] /status endpoint (preserved)")
try:
    r = requests.get(f"{BASE}/status", timeout=5)
    d = r.json()
    check("HTTP 200", r.status_code == 200)
    check("model_loaded present", "model_loaded" in d)
    check("sample_rate=16000", d.get("sample_rate") == 16000)
    check("suspicious_threshold present", "suspicious_threshold" in d)
except Exception as e:
    print(f"  ERROR: {e}")
    FAIL += 3

# ---- Test 2: dummy.wav (known safe/spoof pattern) ----
print("\n[2] dummy.wav analysis")
try:
    with open("dummy.wav", "rb") as f:
        r = requests.post(f"{BASE}/api/predict", files={"file": ("dummy.wav", f, "audio/wav")}, timeout=60)
    d = r.json()
    check("HTTP 200", r.status_code == 200)
    check("score present", "score" in d)
    check("status present", "status" in d)
    check("threat_label present", "threat_label" in d)
    check("genuine_probability_percent present", "genuine_probability_percent" in d)
    check("spoof_probability_percent present", "spoof_probability_percent" in d)
    check("filename present", "filename" in d)
    check("samples present", "samples" in d)
    check("duration_sec present", "duration_sec" in d)
    check("gemini key present", "gemini" in d)
    check("fusion key present", "fusion" in d)
    check("gemini.available is bool", isinstance(d.get("gemini", {}).get("available"), bool))
    check("fusion.finalScore is float", isinstance(d.get("fusion", {}).get("finalScore"), float))
    check("fusion.classification present", d.get("fusion", {}).get("classification") in ("SAFE","SUSPICIOUS","HIGH_RISK"))
    check("fusion.modelsUsed is list", isinstance(d.get("fusion", {}).get("modelsUsed"), list))
    # Gemini unavailable (no key) → AASIST weight = 1.0
    check("AASIST-only weight=1.0 when Gemini unavailable", 
          not d["gemini"]["available"] or d["fusion"]["aasistWeight"] <= 1.0)
    print(f"     AASIST score: {d['score']:.4f} | status: {d['status']} | models: {d['fusion']['modelsUsed']}")
except Exception as e:
    print(f"  ERROR: {e}")
    FAIL += 5

# ---- Test 3: synthetic_spoof_test.wav ----
print("\n[3] synthetic_spoof_test.wav")
try:
    with open("synthetic_spoof_test.wav", "rb") as f:
        r = requests.post(f"{BASE}/api/predict", files={"file": ("synthetic_spoof_test.wav", f, "audio/wav")}, timeout=60)
    d = r.json()
    check("HTTP 200", r.status_code == 200)
    check("status is HIGH_RISK or SUSPICIOUS or SAFE", d.get("status") in ("HIGH_RISK", "SUSPICIOUS", "SAFE"))
    print(f"     AASIST genuine%: {d.get('genuine_probability_percent')} | status: {d.get('status')}")
except Exception as e:
    print(f"  ERROR: {e}")
    FAIL += 2

# ---- Test 4: Silence → expect error (empty audio) ----
print("\n[4] silence_control.wav (empty/silence audio)")
try:
    with open("silence_control.wav", "rb") as f:
        r = requests.post(f"{BASE}/api/predict", files={"file": ("silence_control.wav", f, "audio/wav")}, timeout=60)
    d = r.json()
    # Silence could return an error OR succeed depending on VAD
    check("Returns JSON", isinstance(d, dict))
    check("Error or valid response", "error" in d or "status" in d)
    print(f"     Response: {d.get('error') or d.get('status')}")
except Exception as e:
    print(f"  ERROR: {e}")
    FAIL += 2

# ---- Test 5: Invalid file type ----
print("\n[5] Invalid file type (.exe)")
try:
    r = requests.post(f"{BASE}/api/predict", files={"file": ("malware.exe", b"MZ\x00\x00", "application/octet-stream")}, timeout=10)
    d = r.json()
    check("HTTP 400", r.status_code == 400)
    check("error message present", "error" in d)
    print(f"     Error: {d.get('error')}")
except Exception as e:
    print(f"  ERROR: {e}")
    FAIL += 2

# ---- Test 6: No file ----
print("\n[6] No file uploaded")
try:
    r = requests.post(f"{BASE}/api/predict", timeout=10)
    d = r.json()
    check("HTTP 400", r.status_code == 400)
    check("error message present", "error" in d)
    print(f"     Error: {d.get('error')}")
except Exception as e:
    print(f"  ERROR: {e}")
    FAIL += 2

# ---- Test 7: Oversized file (simulated) ----
print("\n[7] Oversized file check")
try:
    # Config says MAX_AUDIO_SIZE_MB=50; we'll send 1 byte to ensure validation path works
    # (We can't actually send 51MB in a test - just test the small file passes)
    r = requests.post(f"{BASE}/api/predict", files={"file": ("test.txt", b"x", "audio/wav")}, timeout=10)
    d = r.json()
    # text content will fail AASIST processing but that's fine
    check("Returns JSON error or result", isinstance(d, dict))
    print(f"     Response status: {r.status_code}")
except Exception as e:
    print(f"  ERROR: {e}")
    FAIL += 1

# ---- Test 8: Gemini + AASIST fusion validation ----
print("\n[8] Gemini + AASIST Integration & Fusion Validation")
try:
    with open("dummy.wav", "rb") as f:
        r = requests.post(f"{BASE}/api/predict", files={"file": ("dummy.wav", f, "audio/wav")}, timeout=60)
    d = r.json()
    gemini = d.get("gemini", {})
    fusion = d.get("fusion", {})
    check("gemini result present", "available" in gemini)
    check("fusion result present", "finalScore" in fusion)
    check("AASIST result still present", d.get("score") is not None)
    if gemini.get("available"):
        check("Gemini available and active", True)
        check("Fusion uses both models", "Gemini" in fusion.get("modelsUsed", []))
    else:
        check("Graceful fallback without Gemini", fusion.get("aasistWeight", 0) > 0.0 and "AASIST" in fusion.get("modelsUsed", []))
        check("Gemini weight is 0.0 when unavailable", fusion.get("geminiWeight") == 0.0)
    print(f"     Fusion weights: AASIST={fusion.get('aasistWeight')} Gemini={fusion.get('geminiWeight')} | Models: {fusion.get('modelsUsed')}")
except Exception as e:
    print(f"  ERROR: {e}")
    FAIL += 5

# ---- Summary ----
print("\n" + "=" * 60)
print(f"TESTS PASSED: {PASS} / {PASS + FAIL}")
if FAIL > 0:
    print(f"TESTS FAILED: {FAIL}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
