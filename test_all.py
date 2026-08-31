import os
import json
from app import app, system

test_files = [
    "dummy.wav",
    "silence_control.wav",
    "synthetic_spoof_test.wav",
    "human_libri1_male.wav"
]

client = app.test_client()

print("Status endpoint:")
status_res = client.get('/status')
print(json.dumps(status_res.json, indent=2))

for filename in test_files:
    if not os.path.exists(filename):
        print(f"\nSkipping {filename}, not found.")
        continue
    print(f"\n--- Testing /api/predict with {filename} ---")
    with open(filename, 'rb') as f:
        data = {
            'file': (f, filename)
        }
        res = client.post('/api/predict', data=data, content_type='multipart/form-data')
        print(f"Status: {res.status_code}")
        print(json.dumps(res.json, indent=2))
