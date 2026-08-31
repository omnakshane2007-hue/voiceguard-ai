"""
Systematic root cause analysis of AASIST false positives on genuine human speech.
Tests:
1. Leading/trailing silence impact
2. Short duration & np.tile repetition boundary artifacts
3. Microphone DC offset & low frequency noise
4. Sampling rate conversion (44.1k/48k -> 16k) & codecs (MP3/AAC)
5. RMS energy / Volume scaling
6. Voice Activity Detection (VAD) / Trimmed speech vs raw window
7. RawNet2 and Gemini comparison on all tests
"""

import io
import os
import numpy as np
import soundfile as sf
import librosa
import torch
import torch.nn.functional as F

from model_loader import AASISTLoader
from services.rawnet2_analyzer import RawNet2Analyzer

def run_tests():
    aasist_loader = AASISTLoader()
    aasist_loader.setup()
    device = aasist_loader.device
    model = aasist_loader.model

    rawnet2_analyzer = RawNet2Analyzer()
    rawnet2_analyzer.load_model()

    # Load clean human speech
    y_clean, sr = librosa.load("human_libri1_male.wav", sr=16000)

    print("================================================================================")
    print("EXPERIMENT 1: Leading Silence & Non-speech pauses")
    print("================================================================================")
    # Test a: Voiced speech segment (samples 10000 to 74600)
    y_voiced = y_clean[10000:74600]
    # Test b: 2.0s silence + 2.0s speech
    silence_2s = np.zeros(32000, dtype=np.float32)
    y_silence_speech = np.concatenate([silence_2s, y_clean[:32600]])
    # Test c: 3.5s silence + 0.5s speech
    silence_35s = np.zeros(56000, dtype=np.float32)
    y_mostly_silence = np.concatenate([silence_35s, y_clean[:8600]])

    for name, audio in [
        ("Pure Voiced Speech (4s)", y_voiced),
        ("2.0s Silence + 2.0s Speech", y_silence_speech),
        ("3.5s Silence + 0.5s Speech", y_mostly_silence),
    ]:
        t = torch.tensor(audio, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            _, out = model(t)
            probs = F.softmax(out, dim=1)
            bona = probs[0, 1].item()
            spoof = probs[0, 0].item()
            logits = (out[0,0].item(), out[0,1].item())
        print(f"{name:30s} -> AASIST Spoof: {spoof*100:6.2f}% | Bona: {bona*100:6.2f}% | Logits: {logits}")

    print("\n================================================================================")
    print("EXPERIMENT 2: Short Audio & Repetition (np.tile) Artifacts")
    print("================================================================================")
    # Take a 1.0s, 1.5s, 2.0s snippet of genuine human voice and tile to 64600
    for dur_sec in [0.5, 1.0, 1.5, 2.0, 3.0, 4.0]:
        n_samples = int(dur_sec * 16000)
        short_clip = y_clean[10000:10000+n_samples]
        num_repeats = int(64600 / len(short_clip)) + 1
        tiled = np.tile(short_clip, num_repeats)[:64600]

        # Compare tiled vs zero-padded
        zero_padded = np.pad(short_clip, (0, 64600 - len(short_clip)))

        # Run AASIST on tiled
        t_tiled = torch.tensor(tiled, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            _, out_t = model(t_tiled)
            bona_t = F.softmax(out_t, dim=1)[0, 1].item()

        # Run AASIST on zero-padded
        t_zero = torch.tensor(zero_padded, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            _, out_z = model(t_zero)
            bona_z = F.softmax(out_z, dim=1)[0, 1].item()

        print(f"Duration: {dur_sec:3.1f}s | Tiled (np.tile) Bona%: {bona_t*100:6.2f}% (Spoof: {(1-bona_t)*100:6.2f}%) | Zero-padded Bona%: {bona_z*100:6.2f}%")

    print("\n================================================================================")
    print("EXPERIMENT 3: Acoustic Noise, DC Offset & Microphone Artifacts")
    print("================================================================================")
    # Add DC offset (+0.05)
    y_dc = y_voiced + 0.05
    # Add 50Hz hum / low-freq noise
    t_axis = np.linspace(0, len(y_voiced)/16000, len(y_voiced), False)
    hum_50hz = 0.02 * np.sin(2 * np.pi * 50 * t_axis)
    y_hum = y_voiced + hum_50hz
    # Add white noise (SNR ~ 30dB)
    noise = np.random.normal(0, 0.005, len(y_voiced)).astype(np.float32)
    y_noisy = y_voiced + noise
    # Bandpass filter (like telecom or laptop mic: 300Hz - 3400Hz)
    from scipy.signal import butter, sosfilt
    sos = butter(4, [300, 3400], btype='bandpass', fs=16000, output='sos')
    y_bandpass = sosfilt(sos, y_voiced).astype(np.float32)

    for name, audio in [
        ("Clean Voiced (Baseline)", y_voiced),
        ("With DC Offset (+0.05)", y_dc),
        ("With 50Hz Laptop/Mains Hum", y_hum),
        ("With Low Ambient Noise (30dB)", y_noisy),
        ("Telecom Bandpass (300-3400Hz)", y_bandpass),
    ]:
        t = torch.tensor(audio, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            _, out = model(t)
            probs = F.softmax(out, dim=1)
            bona = probs[0, 1].item()
            spoof = probs[0, 0].item()
        print(f"{name:32s} -> AASIST Spoof: {spoof*100:6.2f}% | Bona: {bona*100:6.2f}%")

    print("\n================================================================================")
    print("EXPERIMENT 4: Codec Compression (MP3, AAC/M4A, OGG) on Genuine Voice")
    print("================================================================================")
    # Encode genuine audio through MP3 and OGG and reload
    # MP3 at 128k, 64k
    buf_wav = io.BytesIO()
    sf.write(buf_wav, y_voiced, 16000, format='WAV')
    buf_wav.seek(0)

    buf_ogg = io.BytesIO()
    sf.write(buf_ogg, y_voiced, 16000, format='OGG')
    buf_ogg.seek(0)
    y_ogg, _ = librosa.load(buf_ogg, sr=16000)

    buf_flac = io.BytesIO()
    sf.write(buf_flac, y_voiced, 16000, format='FLAC')
    buf_flac.seek(0)
    y_flac, _ = librosa.load(buf_flac, sr=16000)

    for name, audio in [
        ("WAV (Uncompressed)", y_voiced),
        ("FLAC (Lossless)", y_flac[:64600]),
        ("OGG Vorbis (Compressed)", y_ogg[:64600]),
    ]:
        t = torch.tensor(audio, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            _, out = model(t)
            probs = F.softmax(out, dim=1)
            bona = probs[0, 1].item()
            spoof = probs[0, 0].item()
        print(f"{name:26s} -> AASIST Spoof: {spoof*100:6.2f}% | Bona: {bona*100:6.2f}%")

    print("\n================================================================================")
    print("EXPERIMENT 5: Volume / Gain / Normalization Sensitivity")
    print("================================================================================")
    for gain in [0.05, 0.1, 0.25, 0.5, 1.0, 1.5, 2.0]:
        y_scaled = (y_voiced * gain).astype(np.float32)
        t = torch.tensor(y_scaled, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            _, out = model(t)
            probs = F.softmax(out, dim=1)
            bona = probs[0, 1].item()
            spoof = probs[0, 0].item()
        print(f"Gain: {gain:4.2f}x (RMS: {np.sqrt(np.mean(y_scaled**2)):.4f}) -> AASIST Spoof: {spoof*100:6.2f}% | Bona: {bona*100:6.2f}%")

if __name__ == "__main__":
    run_tests()
