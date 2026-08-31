"""
Pre-verification script to test proposed AASIST preprocessing enhancements
across genuine, short, long, synthetic, dummy, and silence audio.
"""

import numpy as np
import soundfile as sf
import librosa
import torch
import torch.nn.functional as F

import config
from model_loader import AASISTLoader

def preprocess_aasist_old(y, max_len=64600):
    """Old implementation with np.tile and blind head slice."""
    if len(y) >= max_len:
        return y[:max_len]
    num_repeats = int(max_len / len(y)) + 1
    return np.tile(y, num_repeats)[:max_len]

def preprocess_aasist_new(y, max_len=64600):
    """
    Enhanced speech-preserving preprocessing:
    1. VAD / energy-based trimming of leading/trailing silence
    2. Energy-dense window selection for audio > 64600 samples
    3. Zero-padding (no np.tile) for audio < 64600 samples
    """
    if len(y) == 0 or np.max(np.abs(y)) < 0.0001:
        raise ValueError("Audio file appears to be empty or pure silence.")

    # 1. Trim leading and trailing silence (top_db=35 for speech)
    try:
        y_trimmed, _ = librosa.effects.trim(y, top_db=35, frame_length=1024, hop_length=256)
        # If trimmed version has at least 0.25s of audio, use it; otherwise fallback to y
        if len(y_trimmed) >= 4000:
            y_use = y_trimmed
        else:
            y_use = y
    except Exception:
        y_use = y

    n_samples = len(y_use)

    # 2. Window selection if longer than max_len (64600)
    if n_samples > max_len:
        # Find 64,600-sample window with highest RMS energy
        step = 8000  # 0.5s step
        best_start = 0
        max_energy = -1.0
        for start in range(0, n_samples - max_len + 1, step):
            chunk = y_use[start:start + max_len]
            energy = np.mean(chunk ** 2)
            if energy > max_energy:
                max_energy = energy
                best_start = start
        y_processed = y_use[best_start:best_start + max_len]
    elif n_samples == max_len:
        y_processed = y_use
    else:
        # 3. Speech-preserving padding for audio < 64600 samples (zero-padding)
        # Zero-pad on the right (or centered) without periodic tiling
        y_processed = np.pad(y_use, (0, max_len - n_samples), mode='constant', constant_values=0.0)

    return y_processed.astype(np.float32)


def run_benchmark():
    loader = AASISTLoader()
    loader.setup()
    model = loader.model
    device = loader.device

    # Load audio test files
    y_libri1, _ = librosa.load("human_libri1_male.wav", sr=16000)
    y_libri2, _ = librosa.load("human_libri2_male.wav", sr=16000)
    y_libri3, _ = librosa.load("human_libri3_female.wav", sr=16000)
    y_synth, _ = librosa.load("synthetic_spoof_test.wav", sr=16000)
    y_dummy, _ = librosa.load("dummy.wav", sr=16000)

    # Create short 1.5s human voice clips
    y_short_male = y_libri1[10000:10000+24000] # 1.5s
    y_short_female = y_libri3[10000:10000+24000] # 1.5s

    # Create long human voice clip with 2.5s leading silence
    y_leading_silence = np.concatenate([np.zeros(40000, dtype=np.float32), y_libri2])

    test_cases = [
        ("Genuine Male (1.5s short)", y_short_male),
        ("Genuine Female (1.5s short)", y_short_female),
        ("Genuine Voice (Full Long 14.8s)", y_libri1),
        ("Genuine Voice (Full Long 16.7s)", y_libri2),
        ("Genuine Voice (With 2.5s Leading Silence)", y_leading_silence),
        ("Synthetic Spoof Test (synthetic_spoof_test.wav)", y_synth),
        ("Synthetic Tone (dummy.wav)", y_dummy),
    ]

    print("=" * 95)
    print(f"{'TEST CASE':45s} | {'BEFORE (np.tile)':22s} | {'AFTER (New Preproc)':22s}")
    print("=" * 95)

    for name, raw_y in test_cases:
        # Before
        y_old = preprocess_aasist_old(raw_y)
        t_old = torch.tensor(y_old, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            _, out_old = model(t_old)
            p_old = F.softmax(out_old, dim=1)
            bona_old = p_old[0, 1].item()
            spoof_old = p_old[0, 0].item()

        # After
        y_new = preprocess_aasist_new(raw_y)
        t_new = torch.tensor(y_new, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            _, out_new = model(t_new)
            p_new = F.softmax(out_new, dim=1)
            bona_new = p_new[0, 1].item()
            spoof_new = p_new[0, 0].item()

        before_str = f"Spoof: {spoof_old*100:5.2f}% (Bona: {bona_old*100:5.2f}%)"
        after_str = f"Spoof: {spoof_new*100:5.2f}% (Bona: {bona_new*100:5.2f}%)"
        print(f"{name:45s} | {before_str:22s} | {after_str:22s}")

if __name__ == "__main__":
    run_benchmark()
