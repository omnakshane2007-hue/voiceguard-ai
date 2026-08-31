import os
import urllib.request
import hashlib
import sys

# Define models to download
MODELS = {
    "AASIST.pth": {
        "url": "https://raw.githubusercontent.com/clovaai/aasist/main/models/weights/AASIST.pth",
        "sha256": "51d2d9cf0738172f61e2a384ec50a54a55363240f67c971ed55a92435bc1a1c0",
        "path": os.path.join("aasist", "models", "weights", "AASIST.pth")
    },
    "pre_trained_DF_RawNet2.pth": {
        "url": "https://huggingface.co/MattyB95/pre_trained_DF_RawNet2/resolve/main/pre_trained_DF_RawNet2.pth",
        "sha256": "52d8ad5f524a0f600c7c876d7a157a8f06c44a03504d0b2795c852f5e42c9127",
        "path": os.path.join("aasist", "models", "weights", "pre_trained_DF_RawNet2.pth")
    }
}

def compute_sha256(filepath):
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest().lower()
    except Exception as e:
        print(f"Error computing hash for {filepath}: {e}")
        return None

def download_file(url, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    print(f"Downloading {url} to {filepath}...")
    try:
        urllib.request.urlretrieve(url, filepath)
        print(f"Downloaded successfully: {filepath}")
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False

def check_and_download(name, info):
    filepath = info["path"]
    expected_hash = info["sha256"]
    
    if os.path.exists(filepath):
        print(f"Checking existing file for {name}...")
        actual_hash = compute_sha256(filepath)
        if actual_hash == expected_hash:
            print(f"  [OK] {name} is valid and ready.")
            return True
        else:
            print(f"  [WARN] Hash mismatch for {name}. Expected: {expected_hash}, got: {actual_hash}")
            print(f"    This usually means it's a Git LFS pointer instead of the actual file.")
            print(f"    Overwriting with direct download...")
    else:
        print(f"File {name} not found locally.")

    if download_file(info["url"], filepath):
        actual_hash = compute_sha256(filepath)
        if actual_hash == expected_hash:
            print(f"  [OK] {name} downloaded and verified successfully.")
            return True
        else:
            print(f"  [ERROR] FATAL: Downloaded file hash mismatch for {name}.")
            return False
    return False

def main():
    print("=== Model Weights Deployment Checker ===")
    all_good = True
    for name, info in MODELS.items():
        if not check_and_download(name, info):
            all_good = False
            
    if all_good:
        print("All model weights are verified and ready for deployment.")
        sys.exit(0)
    else:
        print("ERROR: Failed to prepare all model weights.")
        sys.exit(1)

if __name__ == "__main__":
    main()
