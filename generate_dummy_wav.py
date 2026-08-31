import wave
import struct
import math

def generate_dummy_wav(filename, duration_seconds=4, sample_rate=16000, frequency=440.0):
    num_samples = int(duration_seconds * sample_rate)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2) # 16-bit
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            # Generate a simple sine wave
            value = int(32767.0 * math.sin(2.0 * math.pi * frequency * i / sample_rate))
            data = struct.pack('<h', value)
            wav_file.writeframesraw(data)

if __name__ == "__main__":
    generate_dummy_wav("dummy.wav")
    print("Created dummy.wav")
