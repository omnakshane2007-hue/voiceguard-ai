"""
VOICEGUARD AI - Live Gemini Integration Verification
Tests real Gemini API call with actual audio file.
Does NOT print the API key.
"""
import requests
import json
import sys

BASE = "http://localhost:5000"

print("=" * 60)
print("VOICEGUARD AI - Live Gemini Verification")
print("=" * 60)

# ---- Verify key is loaded (without printing it) ----
print("\n[PREFLIGHT] Checking config...")
import os, sys
sys.path.insert(0, '.')
import config
key_present = bool(config.GEMINI_API_KEY)
print(f"  Gemini API key detected: {'YES' if key_present else 'NO'}")
print(f"  Key length: {len(config.GEMINI_API_KEY)} chars")
print(f"  AASIST weight: {config.AASIST_WEIGHT}")
print(f"  Gemini weight: {config.GEMINI_WEIGHT}")
print(f"  Timeout: {config.GEMINI_TIMEOUT_SECONDS}s")

# ---- Real API test: synthetic spoof file ----
print("\n[TEST] Calling /api/predict with synthetic_spoof_test.wav...")
print("  (This will make a real Gemini API call - may take 5-30s)")

try:
    with open("synthetic_spoof_test.wav", "rb") as f:
        resp = requests.post(
            f"{BASE}/api/predict",
            files={"file": ("synthetic_spoof_test.wav", f, "audio/wav")},
            timeout=120
        )
    
    data = resp.json()
    print(f"\n  HTTP status: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"  ERROR: {data.get('error')}")
        sys.exit(1)

    # ---- AASIST ----
    print("\n--- AASIST ---")
    aasist_score = data.get("score")
    print(f"  Score (genuine_prob): {aasist_score:.6f}")
    print(f"  Genuine%: {data.get('genuine_probability_percent')}%")
    print(f"  Spoof%: {data.get('spoof_probability_percent')}%")
    print(f"  Status: {data.get('status')}")
    print(f"  Threat: {data.get('threat_label')}")
    aasist_ok = aasist_score is not None
    print(f"  AASIST: {'SUCCESS' if aasist_ok else 'FAILED'}")

    # ---- Gemini ----
    gemini = data.get("gemini", {})
    print("\n--- Gemini ---")
    g_available = gemini.get("available", False)
    g_classification = gemini.get("classification", "N/A")
    g_suspicion = gemini.get("suspicionScore")
    g_confidence = gemini.get("confidence")
    g_evidence = gemini.get("evidence", [])
    g_segments = gemini.get("suspiciousSegments", [])
    g_limits = gemini.get("limitations", [])
    
    print(f"  Available: {g_available}")
    print(f"  Classification: {g_classification}")
    print(f"  Suspicion score: {g_suspicion}")
    print(f"  Confidence: {g_confidence}")
    print(f"  Evidence items: {len(g_evidence)}")
    if g_evidence:
        for ev in g_evidence[:3]:
            print(f"    - {ev}")
    print(f"  Suspicious segments: {len(g_segments)}")
    print(f"  Limitations: {len(g_limits)}")
    if g_limits:
        for lim in g_limits:
            print(f"    * {lim}")
    gemini_ok = g_available
    print(f"  Gemini: {'SUCCESS' if gemini_ok else 'FAILED'}")
    if not gemini_ok:
        print(f"  [!] Reason: {g_limits}")

    # ---- Fusion ----
    fusion = data.get("fusion", {})
    print("\n--- Fusion ---")
    f_score = fusion.get("finalScore")
    f_spoof = fusion.get("finalSpoof")
    f_cls = fusion.get("classification")
    f_models = fusion.get("modelsUsed", [])
    f_aw = fusion.get("aasistWeight")
    f_gw = fusion.get("geminiWeight")
    f_conf = fusion.get("confidence")
    
    print(f"  Final genuine score: {f_score}")
    print(f"  Final spoof score:   {f_spoof}")
    print(f"  Classification: {f_cls}")
    print(f"  Models used: {f_models}")
    print(f"  AASIST weight: {f_aw}")
    print(f"  Gemini weight: {f_gw}")
    print(f"  Combined confidence: {f_conf}%")
    
    # Verify fusion math
    if gemini_ok and aasist_ok:
        expected_spoof = round((1 - aasist_score) * f_aw + (g_suspicion / 100.0) * f_gw, 4)
        actual_spoof = round(f_spoof, 4)
        math_ok = abs(expected_spoof - actual_spoof) < 0.01
        print(f"  Math check (expected ~{expected_spoof}, got {actual_spoof}): {'OK' if math_ok else 'MISMATCH'}")
    
    fusion_ok = f_score is not None and f_cls is not None
    print(f"  Fusion: {'SUCCESS' if fusion_ok else 'FAILED'}")

    # ---- All original fields still present ----
    required = ['score','status','threat_label','filename','samples','duration_sec',
                'genuine_probability_percent','spoof_probability_percent']
    missing = [k for k in required if k not in data]
    backward_compat = len(missing) == 0
    print(f"\n--- Backward Compatibility ---")
    print(f"  All original fields preserved: {'YES' if backward_compat else 'NO - missing: ' + str(missing)}")

    # ---- Summary ----
    print("\n" + "=" * 60)
    print("FINAL REPORT")
    print("=" * 60)
    print(f"Gemini API key detected: {'YES' if key_present else 'NO'}")
    print(f"Gemini API call: {'SUCCESS' if gemini_ok else 'FAILED'}")
    print(f"AASIST: {'SUCCESS' if aasist_ok else 'FAILED'}")
    print(f"Fusion: {'SUCCESS' if fusion_ok else 'FAILED'}")
    print()
    print("Gemini result:")
    print(f"  Classification: {g_classification}")
    print(f"  Suspicion score: {g_suspicion}")
    print(f"  Confidence: {g_confidence}")

except Exception as e:
    print(f"\n  EXCEPTION: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
