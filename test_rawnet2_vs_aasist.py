"""
Compare RawNet2, AASIST, and Gemini on short tiled audio vs zero-padded audio vs full audio.
"""

import numpy as np
import soundfile as sf
import librosa
import torch
import torch.nn.functional as F

from model_loader import AASISTLoader
from services.rawnet2_analyzer import RawNet2Analyzer

def compare():
    aasist_loader = AASISTLoader()
    aasist_loader.setup()
    device = aasist_loader.device
    aasist_model = aasist_loader.model

    rawnet2 = RawNet2Analyzer()
    rawnet2.load_model()

    y_clean, sr = librosa.load("human_libri1_male.wav", sr=16000)

    # 1.5s human speech clip
    short_15s = y_clean[10000:10000+24000] # 1.5s

    # Tiling (np.tile)
    tiled_15s = np.tile(short_15s, int(64600/len(short_15s))+1)[:64600]

    # Zero-padding
    zero_15s = np.pad(short_15s, (0, 64600 - len(short_15s)))

    # Continuous 4.0s speech
    full_40s = y_clean[10000:10000+64600]

    print("=================================================================")
    print("COMPARISON: AASIST vs RAWNET2 ON SAME AUDIO")
    print("=================================================================")

    for label, audio in [
        ("1.5s Human Voice (Tiled with np.tile)", tiled_15s),
        ("1.5s Human Voice (Zero-Padded)", zero_15s),
        ("4.0s Full Human Voice (Continuous)", full_40s),
    ]:
        # AASIST
        t_a = torch.tensor(audio, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            _, out_a = aasist_model(t_a)
            p_a = F.softmax(out_a, dim=1)
            aasist_bona = p_a[0, 1].item()
            aasist_spoof = p_a[0, 0].item()

        # RawNet2
        t_r = torch.tensor(audio, dtype=torch.float32).unsqueeze(0).to(rawnet2.device)
        with torch.no_grad():
            _, out_r = rawnet2.model(t_r)
            p_r = torch.exp(out_r)
            rawnet_bona = p_r[0, 1].item()
            rawnet_spoof = 1.0 - rawnet_bona

        print(f"\n[{label}]")
        print(f"  AASIST  -> Spoof: {aasist_spoof*100:5.2f}% | Genuine: {aasist_bona*100:5.2f}%")
        print(f"  RawNet2 -> Spoof: {rawnet_spoof*100:5.2f}% | Genuine: {rawnet_bona*100:5.2f}%")

if __name__ == "__main__":
    compare()
