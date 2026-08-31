"""
Compare RawNet2 DF vs LA checkpoints on genuine human speech and synthetic speech.
"""

import torch
import librosa
import numpy as np
from services.rawnet2_analyzer import RawNet2Analyzer

def test_checkpoints():
    y_human1, _ = librosa.load("human_libri1_male.wav", sr=16000)
    y_human3, _ = librosa.load("human_libri3_female.wav", sr=16000)
    y_synth, _ = librosa.load("synthetic_spoof_test.wav", sr=16000)

    y_human1 = np.asarray(y_human1)
    y_human3 = np.asarray(y_human3)
    y_synth = np.asarray(y_synth)

    for ckpt_name, ckpt_path in [
        ("RawNet2 (DF Checkpoint)", "aasist/models/weights/pre_trained_DF_RawNet2.pth"),
        ("RawNet2 (LA Checkpoint)", "aasist/models/weights/pre_trained_LA_RawNet2.pth"),
    ]:
        print(f"\n=======================================================")
        print(f"EVALUATING {ckpt_name}")
        print(f"=======================================================")
        r2 = RawNet2Analyzer(weights_path=ckpt_path)
        r2.load_model()

        for label, y in [
            ("Human Male (4.0s continuous)", y_human1[10000:10000+64600]),
            ("Human Female (4.0s continuous)", y_human3[10000:10000+64600]),
            ("Synthetic Spoof Test (4.0s)", y_synth[:64600]),
        ]:
            t = torch.tensor(y, dtype=torch.float32).unsqueeze(0).to(r2.device)
            with torch.no_grad():
                _, out = r2.model(t)
                # RawNet2 output layer is log_softmax
                exp_out = torch.exp(out)
                spoof_logp = out[0, 0].item()
                bona_logp = out[0, 1].item()
                spoof_p = exp_out[0, 0].item()
                bona_p = exp_out[0, 1].item()
            print(f"  {label:32s} -> Logits: [0 (spoof)]: {spoof_logp:.4f}, [1 (bona)]: {bona_logp:.4f} | Spoof: {spoof_p*100:5.2f}% | Bona: {bona_p*100:5.2f}%")

if __name__ == "__main__":
    test_checkpoints()
