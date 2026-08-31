import queue
# Trigger IDE re-analysis
import threading
try:
    import sounddevice as sd
except (ImportError, OSError):
    sd = None
import numpy as np

import config

class AudioCaptureError(Exception):
    pass

class AudioCapture:
    def __init__(self):
        self.sample_rate = config.SAMPLE_RATE
        self.chunk_samples = config.AUDIO_CHUNK_SAMPLES
        
        # Audio buffer to hold the rolling window
        self.buffer: np.ndarray = np.zeros(self.chunk_samples, dtype=np.float32)
        
        # We process input from sounddevice in small blocks
        # 30ms blocks are ideal for webrtcvad if we want to run VAD continuously,
        # but we can also just run VAD on the extracted chunk.
        self.blocksize = int(self.sample_rate * 0.1) # 100ms blocks from mic
        
        try:
            import webrtcvad # type: ignore
            self.vad = webrtcvad.Vad(config.VAD_MODE)
        except ImportError:
            print("[AudioCapture] webrtcvad not installed, falling back to RMS energy VAD.")
            self.vad = None
            
        self.audio_queue = queue.Queue()
        self.stream = None
        self.is_recording = False
        
        # Lock for buffer operations
        self.buffer_lock = threading.Lock()
        
        # To keep track of how many samples added since last yield
        self.samples_since_yield = 0
        self.yield_threshold = int(config.UPDATE_INTERVAL_SECONDS * self.sample_rate)

    def _audio_callback(self, indata, frames, time_info, status):
        """This is called by sounddevice for each audio block."""
        if status:
            print(f"[AudioCapture] Stream status: {status}")
            
        # indata is shape (frames, channels)
        # We expect mono, so take channel 0
        mono_data = indata[:, 0]
        
        with self.buffer_lock:
            # Shift buffer left by 'frames' and insert new data at the end
            self.buffer[:-frames] = self.buffer[frames:]  # type: ignore
            self.buffer[-frames:] = mono_data  # type: ignore
            
            self.samples_since_yield += frames
            
            # If we have accumulated enough new samples, we yield a chunk
            if self.samples_since_yield >= self.yield_threshold:
                # Put a copy of the current buffer into the queue
                self.audio_queue.put(self.buffer.copy())
                self.samples_since_yield = 0

    def start(self):
        if self.is_recording:
            return
            
        if sd is None:
            print("[AudioCapture] sounddevice not available (running in headless/cloud environment).")
            return

        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                blocksize=self.blocksize,
                callback=self._audio_callback
            )
            self.stream.start()
            self.is_recording = True
            print("[AudioCapture] Started recording.")
        except Exception as e:
            print(f"[AudioCapture] Microphone start skipped: {e}")

    def stop(self):
        if self.is_recording and self.stream:
            self.stream.stop()
            self.stream.close()
            self.is_recording = False
            print("[AudioCapture] Stopped recording.")

    def get_next_chunk(self, timeout=None):
        """
        Blocks until the next chunk of audio is ready.
        Returns a tuple: (audio_data, speech_ratio)
        """
        try:
            chunk = self.audio_queue.get(timeout=timeout)
            speech_ratio = self._compute_speech_ratio(chunk)
            return chunk, speech_ratio
        except queue.Empty:
            return None, 0.0

    def _compute_speech_ratio(self, audio_data):
        """
        Computes the ratio of speech in the given audio chunk using webrtcvad or RMS fallback.
        audio_data is a float32 array in [-1.0, 1.0]
        """
        if self.vad is not None:
            # Convert to 16-bit PCM
            pcm_data = (audio_data * 32767).astype(np.int16)
            
            frame_duration = config.VAD_FRAME_DURATION_MS # 30ms
            frame_length = int(self.sample_rate * (frame_duration / 1000.0)) # 480 samples
            
            num_frames = len(pcm_data) // frame_length
            speech_frames = 0
            
            for i in range(num_frames):
                frame = pcm_data[i * frame_length : (i + 1) * frame_length]
                # webrtcvad expects bytes
                if self.vad.is_speech(frame.tobytes(), self.sample_rate):
                    speech_frames += 1
                    
            if num_frames == 0:
                return 0.0
                
            return speech_frames / float(num_frames)
        else:
            # Fallback to simple RMS energy VAD
            rms = np.sqrt(np.mean(audio_data**2))
            # Assume rms > 0.01 is speech (roughly -40 dBFS)
            if rms > 0.01:
                return 1.0
            else:
                return 0.0
