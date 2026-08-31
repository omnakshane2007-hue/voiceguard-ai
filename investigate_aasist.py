"""
Deep diagnostic script to investigate AASIST, RawNet2, and Gemini
behavior across various audio samples, preprocessing pipelines,
waveform normalizations, and score interpretations.
"""

import io
import json
import os
import sys
import numpy as np
import soundfile as sf
import librosa
import torch
import torch.nn.functional as F

import config
from model_loader import AASISTLoader
from services.rawnet2_analyzer import RawNet2Analyzer

def run_diagnostics():
    print("=" * 80)
    print("AASIST & RAWNET2 DIAGNOSTIC EXPERIMENTATION")
    print("=" * 80)

    # 1. Load AASIST model
    print("\n--- 1. Loading AASIST Model ---")
    aasist_loader = AASISTLoader()
    aasist_loader.setup()
    aasist_model = aasist_loader.model
    device = aasist_loader.device

    # 2. Load RawNet2 model
    print("\n--- 2. Loading RawNet2 Model ---")
    rawnet2_analyzer = RawNet2Analyzer()
    rawnet2_analyzer.load_model()
    rawnet2_model = rawnet2_analyzer.model

    # Check available audio files
    audio_files = [
        "synthetic_spoof_test.wav",
        "dummy.wav",
        "silence_control.wav"
    ]
    # Check if any user uploaded audio or recordings exist in scratch or temp
    for f in os.listdir("."):
        if f.endswith((".wav", ".mp3", ".m4a", ".flac", ".ogg")) and f not in audio_files:
            audio_files.append(f)

    print(f"\nDiscovered test audio files: {audio_files}")

    for filepath in audio_files:
        if not os.path.exists(filepath):
            continue
        print(f"\n=======================================================")
        print(f"ANALYZING FILE: {filepath} ({os.path.getsize(filepath)} bytes)")
        print(f"=======================================================")

        with open(filepath, "rb") as fh:
            raw_bytes = fh.read()

        # Read with soundfile
        try:
            data_sf, sr_sf = sf.read(filepath)
            print(f"[Soundfile Info] shape: {data_sf.shape}, dtype: {data_sf.dtype}, sr: {sr_sf}")
            if data_sf.ndim > 1:
                data_sf = data_sf.mean(axis=1)
            print(f"[Soundfile Signal Stats] min={data_sf.min():.4f}, max={data_sf.max():.4f}, mean={data_sf.mean():.6f}, rms={np.sqrt(np.mean(data_sf**2)):.4f}")
        except Exception as e:
            print(f"[Soundfile Error] {e}")
            data_sf = None
            sr_sf = None

        # Read with librosa as currently done in app.py
        y_librosa, sr_librosa = librosa.load(io.BytesIO(raw_bytes), sr=config.SAMPLE_RATE, mono=True)
        print(f"[Librosa Info] shape: {y_librosa.shape}, dtype: {y_librosa.dtype}, sr: {sr_librosa}")
        print(f"[Librosa Signal Stats] min={y_librosa.min():.4f}, max={y_librosa.max():.4f}, mean={y_librosa.mean():.6f}, rms={np.sqrt(np.mean(y_librosa**2)):.4f}")

        # Test AASIST on different preprocessing variants
        print("\n--- AASIST Output Variations ---")

        # Variant A: App.py current (first 64600 / repeat)
        if len(y_librosa) >= 64600:
            y_app = y_librosa[:64600]
        else:
            num_repeats = int(64600 / len(y_librosa)) + 1
            y_app = np.tile(y_librosa, num_repeats)[:64600]

        t_app = torch.tensor(y_app, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            _, out_app = aasist_model(t_app)
            probs_app = F.softmax(out_app, dim=1)
            logprobs_app = F.log_softmax(out_app, dim=1)
            print(f"Variant A (App.py current):")
            print(f"  Raw Logits: [0 (spoof)]: {out_app[0,0].item():.4f}, [1 (bona)]: {out_app[0,1].item():.4f} (diff={out_app[0,1].item()-out_app[0,0].item():.4f})")
            print(f"  Softmax:    [0 (spoof)]: {probs_app[0,0].item():.6f}, [1 (bona)]: {probs_app[0,1].item():.6f}")
            print(f"  LogSoftmax: [0 (spoof)]: {logprobs_app[0,0].item():.4f}, [1 (bona)]: {logprobs_app[0,1].item():.4f}")
            print(f"  App Score (probs[0,1]): {probs_app[0,1].item():.6f}")

        # Variant B: AASIST Official pad() function from aasist/data_utils.py
        from data_utils import pad as official_pad
        y_official = official_pad(data_sf if (data_sf is not None and sr_sf == 16000) else y_librosa, 64600)
        t_off = torch.tensor(y_official, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            _, out_off = aasist_model(t_off)
            probs_off = F.softmax(out_off, dim=1)
            print(f"Variant B (Official data_utils.pad):")
            print(f"  Raw Logits: [0 (spoof)]: {out_off[0,0].item():.4f}, [1 (bona)]: {out_off[0,1].item():.4f}")
            print(f"  Softmax:    [0 (spoof)]: {probs_off[0,0].item():.6f}, [1 (bona)]: {probs_off[0,1].item():.6f}")

        # Variant C: Peak normalized [-1, 1]
        if np.max(np.abs(y_app)) > 0:
            y_norm = y_app / np.max(np.abs(y_app))
            t_norm = torch.tensor(y_norm, dtype=torch.float32).unsqueeze(0).to(device)
            with torch.no_grad():
                _, out_norm = aasist_model(t_norm)
                probs_norm = F.softmax(out_norm, dim=1)
                print(f"Variant C (Peak-normalized):")
                print(f"  Raw Logits: [0 (spoof)]: {out_norm[0,0].item():.4f}, [1 (bona)]: {out_norm[0,1].item():.4f}")
                print(f"  Softmax:    [0 (spoof)]: {probs_norm[0,0].item():.6f}, [1 (bona)]: {probs_norm[0,1].item():.6f}")

        # Variant D: Sliding window over the full audio if longer than 64600
        if len(y_librosa) > 64600:
            print(f"Variant D (Sliding window across full audio length {len(y_librosa)} samples):")
            step = 32000 # 2 sec step
            win_scores = []
            for start in range(0, len(y_librosa) - 64600 + 1, step):
                chunk = y_librosa[start:start+64600]
                t_chunk = torch.tensor(chunk, dtype=torch.float32).unsqueeze(0).to(device)
                with torch.no_grad():
                    _, out_chunk = aasist_model(t_chunk)
                    p_chunk = F.softmax(out_chunk, dim=1)[0, 1].item()
                    win_scores.append(p_chunk)
                    print(f"  Window [{start}:{start+64600}] -> bona_prob={p_chunk:.4f}, logits=({out_chunk[0,0].item():.2f}, {out_chunk[0,1].item():.2f})")
            print(f"  Mean window bona_prob: {np.mean(win_scores):.4f}")

        # Test RawNet2 on the same file
        print("\n--- RawNet2 Output ---")
        try:
            r2_res = rawnet2_analyzer.analyze(raw_bytes)
            print(f"  RawNet2 result: {r2_res}")
        except Exception as e:
            print(f"  RawNet2 error: {e}")

if __name__ == "__main__":
    run_diagnostics()
