import argparse
import torch
import librosa
import numpy as np

import config
from model_loader import AASISTLoader
from services.audio_preprocessor import preprocess_audio_for_aasist

def main():
    parser = argparse.ArgumentParser(description="Test voice cloning detection on a single file.")
    parser.add_argument("audio_path", type=str, help="Path to the audio file (.wav, .flac, etc.)")
    args = parser.parse_args()
    
    print("Initializing model...")
    loader = AASISTLoader()
    try:
        loader.setup()
    except Exception as e:
        print(f"Error loading model: {e}")
        return
        
    print(f"Loading audio file: {args.audio_path}")
    try:
        y, sr = librosa.load(args.audio_path, sr=config.SAMPLE_RATE, mono=True)
    except Exception as e:
        print(f"Failed to load audio: {e}")
        return
        
    try:
        y_padded = preprocess_audio_for_aasist(y, max_len=config.AUDIO_CHUNK_SAMPLES)
    except ValueError as e:
        print(f"Error: {e}")
        return
        
    audio_tensor = torch.tensor(y_padded, dtype=torch.float32)
    
    print("Running inference...")
    try:
        score = loader.predict(audio_tensor)
        print("="*40)
        print(f"Prediction Score (Genuine Probability): {score:.4f}")
        
        if score <= config.HIGH_RISK_THRESHOLD:
            print("Status: HIGH RISK (Likely Cloned/Synthetic)")
        elif score <= config.SUSPICIOUS_THRESHOLD:
            print("Status: SUSPICIOUS (Potentially Cloned)")
        else:
            print("Status: SAFE (Likely Genuine)")
        print("="*40)
    except Exception as e:
        print(f"Inference failed: {e}")

if __name__ == "__main__":
    main()
