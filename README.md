# Real-Time Voice Cloning Detection Prototype

This prototype captures live microphone audio, processes it using Voice Activity Detection (VAD), and runs the pre-trained AASIST model to detect cloned/synthetic speech.

## Features

- **Real-time Audio Capture**: Uses `sounddevice` to buffer live microphone input.
- **Voice Activity Detection**: Uses `webrtcvad` to only process chunks containing actual speech.
- **Deepfake Detection**: Integrates the AASIST model to score the genuineness of the voice.
- **State Machine**: Uses hysteresis to prevent flickering, transitioning between `SAFE`, `SUSPICIOUS`, and `HIGH_RISK`.
- **Web Dashboard**: A Flask-based UI to visually monitor the risk score in real-time.

## Setup Instructions

1. **Prerequisites**: Ensure you have a working microphone and a Python environment (Python 3.8+ recommended).
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the Dashboard**:
   ```bash
   python app.py
   ```
   *Note: The first time you run this, it will automatically clone the AASIST repository to download the model architecture and weights.*

4. **Access Dashboard**:
   Open a web browser and navigate to `http://localhost:5000/`.

## Testing with an Audio File

You can also test a specific audio file instead of the microphone:
```bash
python test_with_file.py path/to/your_audio.wav
```

You can generate cloned voice samples using popular TTS tools like ElevenLabs or Coqui TTS, and compare the scores against recordings of your actual voice.

## Tested Environment & Limitations

- **Verified OS**: Windows
- **Verified Python Version**: Python 3.10.21 (via `uv`)
- **PyTorch**: 2.13.0+cpu
- **VAD Implementation**: `webrtcvad` may require Microsoft C++ Build Tools to install on Windows. The prototype automatically falls back to an RMS energy-based VAD if `webrtcvad` fails to load.
- **Model Checkpoint**: The AASIST model repository and `AASIST.pth` checkpoint are automatically cloned during the first run.

## Disclaimer

**Risk Assessment Only:** This is a prototype system based on the AASIST model (trained on ASVspoof datasets). It does not guarantee the detection of all novel or future voice-cloning technologies. Use its results as an indicator of risk rather than absolute proof.
