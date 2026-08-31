"""
Test window selection and multi-window averaging strategies for long audio.
"""

import numpy as np
import librosa
import torch
import torch.nn.functional as F
from model_loader import AASISTLoader

def test_strategies():
    loader = AASISTLoader()
    loader.setup()
    model = loader.model
    device = loader.device

    y_libri1, _ = librosa.load("human_libri1_male.wav", sr=16000)
    y_libri2, _ = librosa.load("human_libri2_male.wav", sr=16000)
    y_libri3, _ = librosa.load("human_libri3_female.wav", sr=16000)
    y_synth, _ = librosa.load("synthetic_spoof_test.wav", sr=16000)
    y_dummy, _ = librosa.load("dummy.wav", sr=16000)
    y_short = y_libri1[10000:10000+24000] # 1.5s
    y_leading_silence = np.concatenate([np.zeros(40000, dtype=np.float32), y_libri2])

    test_files = [
        ("Genuine Male (1.5s short)", y_short),
        ("Genuine Libri1 Male (14.8s)", y_libri1),
        ("Genuine Libri2 Male (16.7s)", y_libri2),
        ("Genuine Libri3 Female (13.9s)", y_libri3),
        ("Genuine Libri2 with 2.5s Leading Silence", y_leading_silence),
        ("Synthetic Spoof (synthetic_spoof_test.wav)", y_synth),
        ("Synthetic Tone (dummy.wav)", y_dummy),
    ]

    print("=" * 80)
    print("TESTING PREPROCESSING STRATEGIES")
    print("=" * 80)

    for name, raw_y in test_files:
        # Trim leading and trailing silence
        y_trimmed, _ = librosa.effects.trim(raw_y, top_db=30, frame_length=1024, hop_length=256)
        if len(y_trimmed) < 4000:
            y_trimmed = raw_y

        # Strategy A: First trimmed 64600 (or zero-padded)
        if len(y_trimmed) >= 64600:
            y_a = y_trimmed[:64600]
        else:
            y_a = np.pad(y_trimmed, (0, 64600 - len(y_trimmed)))
        
        t_a = torch.tensor(y_a, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            _, out_a = model(t_a)
            bona_a = F.softmax(out_a, dim=1)[0, 1].item()

        # Strategy B: Multi-window average (up to 3 non-overlapping / 50% overlap windows from trimmed speech)
        if len(y_trimmed) <= 64600:
            bona_b = bona_a
        else:
            scores = []
            # Sample up to 3 windows: start, middle, and 1/3 point
            offsets = [0]
            if len(y_trimmed) >= 96000: # >= 6s
                offsets.append(32000)
            if len(y_trimmed) >= 128000: # >= 8s
                offsets.append(64000)
            for off in offsets:
                w = y_trimmed[off:off+64600]
                t_w = torch.tensor(w, dtype=torch.float32).unsqueeze(0).to(device)
                with torch.no_grad():
                    _, out_w = model(t_w)
                    scores.append(F.softmax(out_w, dim=1)[0, 1].item())
            bona_b = float(np.mean(scores))

        print(f"{name:45s} | Strategy A (Trimmed Head): Bona {bona_a*100:6.2f}% (Spoof {(1-bona_a)*100:6.2f}%) | Strategy B (Multi-Window): Bona {bona_b*100:6.2f}% (Spoof {(1-bona_b)*100:6.2f}%)")

if __name__ == "__main__":
    test_strategies()
