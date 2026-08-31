import unittest
import torch
import numpy as np
import os
import sys
from unittest.mock import patch, MagicMock

import config
from model_loader import AASISTLoader, ModelLoadError
from audio_capture import AudioCapture, AudioCaptureError
from detector import DetectionSystem

class TestVoiceCloningDetection(unittest.TestCase):
    
    @patch('model_loader.os.path.exists')
    def test_missing_model_checkpoint(self, mock_exists):
        # Force model weights path to return False
        def side_effect(path):
            if path == config.MODEL_WEIGHTS_PATH:
                return False
            return True
        mock_exists.side_effect = side_effect
        
        loader = AASISTLoader()
        with self.assertRaises(ModelLoadError) as context:
            loader._ensure_weights_exist()
        self.assertIn("Model weights not found", str(context.exception))

    @patch('sounddevice.InputStream')
    def test_microphone_failure(self, mock_input_stream):
        # Simulate a microphone error
        mock_input_stream.side_effect = Exception("Microphone in use or not found")
        
        capture = AudioCapture()
        with self.assertRaises(AudioCaptureError):
            capture.start()

    def test_silence_detection(self):
        # Create a silent audio chunk
        capture = AudioCapture()
        silent_audio = np.zeros(config.AUDIO_CHUNK_SAMPLES, dtype=np.float32)
        
        speech_ratio = capture._compute_speech_ratio(silent_audio)
        self.assertEqual(speech_ratio, 0.0, "Silent audio should have 0.0 speech ratio")

    def test_noisy_speech_vad(self):
        # Create pure white noise
        capture = AudioCapture()
        np.random.seed(42)
        noise_audio = np.random.uniform(-1.0, 1.0, config.AUDIO_CHUNK_SAMPLES).astype(np.float32)
        
        # VAD might classify white noise as speech or silence, depending on mode,
        # but typically pure random noise is not classified well. 
        # We just want to ensure it doesn't crash.
        speech_ratio = capture._compute_speech_ratio(noise_audio)
        self.assertIsInstance(speech_ratio, float)

    @patch.object(AASISTLoader, 'predict')
    def test_short_audio_padding_in_file_test(self, mock_predict):
        from services.audio_preprocessor import preprocess_audio_for_aasist
        mock_predict.return_value = 0.99
        
        # 1.5 second sine wave (speech-like signal)
        t = np.linspace(0, 1.5, 24000, endpoint=False)
        short_y = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        
        y_padded = preprocess_audio_for_aasist(short_y, max_len=config.AUDIO_CHUNK_SAMPLES)
            
        self.assertEqual(len(y_padded), config.AUDIO_CHUNK_SAMPLES)
        # Verify safe zero padding (tail is zero, no periodic tile)
        self.assertEqual(y_padded[-1], 0.0)
        audio_tensor = torch.tensor(y_padded, dtype=torch.float32)
        
        score = mock_predict(audio_tensor)
        self.assertEqual(score, 0.99)

    def test_detector_state_machine(self):
        system = DetectionSystem()
        
        # Initial state should be SAFE
        self.assertEqual(system.status, config.STATE_SAFE)
        
        # Provide a HIGH_RISK score, but debounce is 2
        system._update_state_machine(config.HIGH_RISK_THRESHOLD - 0.1)
        self.assertEqual(system.status, config.STATE_SAFE) # Should still be SAFE due to debounce
        
        # Provide second HIGH_RISK score
        system._update_state_machine(config.HIGH_RISK_THRESHOLD - 0.1)
        self.assertEqual(system.status, config.STATE_HIGH_RISK) # Now it updates
        
        # Change to SUSPICIOUS
        system._update_state_machine(config.SUSPICIOUS_THRESHOLD - 0.1)
        self.assertEqual(system.status, config.STATE_HIGH_RISK) # Debounce
        
        system._update_state_machine(config.SUSPICIOUS_THRESHOLD - 0.1)
        self.assertEqual(system.status, config.STATE_SUSPICIOUS) # Updated

if __name__ == '__main__':
    unittest.main()
