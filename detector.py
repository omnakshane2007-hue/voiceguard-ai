import threading
import time
try:
    import winsound
except ImportError:
    winsound = None
import numpy as np
from datetime import datetime

import config
from model_loader import AASISTLoader
from audio_capture import AudioCapture

class DetectionSystem:
    def __init__(self):
        self.model_loader = AASISTLoader()
        self.audio_capture = AudioCapture()
        
        # State variables
        self.current_score = -1.0
        self.smoothed_score = -1.0
        self.status = config.STATE_SAFE
        self.last_speech_ratio = 0.0
        self.total_chunks = 0
        self.processed_chunks = 0
        self.last_update_time = None
        self.latest_gemini_result = None
        
        # Gemini Scheduling State
        self.gemini_last_request_time = 0.0
        self.gemini_cooldown_until = 0.0
        self.is_gemini_pending = False
        
        self.prediction_history = []
        
        self.is_running = False
        self.thread = None
        
        self.listeners = []
        
        # Hysteresis configuration
        self.debounce_counter = 0
        self.debounce_threshold = 2 # require 2 consecutive states to change

    def setup(self):
        self.model_loader.setup()

    def add_listener(self, callback):
        self.listeners.append(callback)

    def _emit(self, event_type, data):
        for listener in self.listeners:
            try:
                listener(event_type, data)
            except Exception as e:
                print(f"[DetectionSystem] Listener error: {e}")

    def start(self):
        if self.is_running:
            return
            
        self.audio_capture.start()
        self.is_running = True
        self.thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.thread.start()
        print("[DetectionSystem] Detection loop started.")

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        self.audio_capture.stop()
        print("[DetectionSystem] Detection loop stopped.")

    def _update_state_machine(self, new_smoothed_score):
        # Determine the target state based on thresholds
        if new_smoothed_score <= config.HIGH_RISK_THRESHOLD:
            target_state = config.STATE_HIGH_RISK
        elif new_smoothed_score <= config.SUSPICIOUS_THRESHOLD:
            target_state = config.STATE_SUSPICIOUS
        else:
            target_state = config.STATE_SAFE
            
        # Hysteresis / Debounce logic
        if target_state != self.status:
            self.debounce_counter += 1
            if self.debounce_counter >= self.debounce_threshold:
                self.status = target_state
                self.debounce_counter = 0
                
                # Emit state change alert
                if self.status in [config.STATE_SUSPICIOUS, config.STATE_HIGH_RISK]:
                    self._emit("alert", {"status": self.status, "score": new_smoothed_score})
        else:
            self.debounce_counter = 0

    def update_external_inference(self, score: float, speech_ratio: float = 1.0, state_override: str = None):
        """
        Thread-safe update called when live audio chunks arrive from browser stream.
        Maintains moving average smoothing and hysteresis state machine.
        """
        self.total_chunks += 1
        self.processed_chunks += 1
        self.last_speech_ratio = float(speech_ratio)
        self.current_score = float(score)
        self.last_update_time = datetime.now().isoformat()

        self.prediction_history.append(self.current_score)
        if len(self.prediction_history) > config.SMOOTHING_WINDOW:
            self.prediction_history.pop(0)

        self.smoothed_score = float(np.mean(self.prediction_history))

        if state_override:
            self.status = state_override
            if self.status in [config.STATE_SUSPICIOUS, config.STATE_HIGH_RISK]:
                self._emit("alert", {"status": self.status, "score": self.smoothed_score})
        else:
            self._update_state_machine(self.smoothed_score)

        return self.status, self.smoothed_score

    def update_gemini_result(self, result: dict):
        """Thread-safe update of the latest asynchronous Gemini analysis result."""
        self.latest_gemini_result = result
        print(f"[DetectionSystem] Gemini result updated: {result.get('classification', 'UNKNOWN')}")

    def _detection_loop(self):
        chunk_number = 0
        while self.is_running:
            try:
                audio_chunk, speech_ratio = self.audio_capture.get_next_chunk(timeout=1.0)
                
                if audio_chunk is None:
                    continue
                    
                chunk_number += 1
                self.total_chunks = chunk_number
                self.last_speech_ratio = float(speech_ratio)
                self.last_update_time = datetime.now().isoformat()
                
                # Only run model if there is enough speech
                if speech_ratio >= 0.5:
                    self.processed_chunks += 1
                    import torch
                    audio_tensor = torch.tensor(audio_chunk, dtype=torch.float32)
                    
                    score = self.model_loader.predict(audio_tensor)
                    self.current_score = score
                    
                    self.prediction_history.append(score)
                    if len(self.prediction_history) > config.SMOOTHING_WINDOW:
                        self.prediction_history.pop(0)
                        
                    self.smoothed_score = np.mean(self.prediction_history)
                    
                    self._update_state_machine(self.smoothed_score)
                    
                    # Logging
                    timestamp = datetime.now().isoformat()
                    print(f"[{timestamp}] Chunk {chunk_number:04d} | Speech: {speech_ratio:.2f} | Score: {self.current_score:.4f} | Smoothed: {self.smoothed_score:.4f} | Status: {self.status}")
                else:
                    # Not enough speech
                    print(f"[{datetime.now().isoformat()}] Chunk {chunk_number:04d} | Speech: {speech_ratio:.2f} (Skipping model inference)")
                    
            except Exception as e:
                print(f"[DetectionSystem] Error in detection loop: {e}")
                
# Optional Alert Implementation (Winsound)
def winsound_alert_listener(event_type, data):
    if winsound is not None and event_type == "alert":
        try:
            status = data.get("status")
            if status == config.STATE_HIGH_RISK:
                # Play an aggressive beep
                winsound.Beep(1000, 500)
            elif status == config.STATE_SUSPICIOUS:
                # Play a mild beep
                winsound.Beep(500, 300)
        except Exception:
            pass
