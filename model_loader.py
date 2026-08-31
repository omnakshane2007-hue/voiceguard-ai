import os
# Trigger IDE re-analysis
import sys
import json
import subprocess
try:
    import torch
    import torch.nn.functional as F
except ImportError:
    torch = None
    F = None

import config

class ModelLoadError(Exception):
    pass

class AASISTLoader:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu") if torch is not None else "cpu"
        self.model = None

    def setup(self):
        """Ensures the repository is cloned and the model is loaded."""
        self._ensure_repo_cloned()
        self._ensure_weights_exist()
        self._load_model()

    def _ensure_repo_cloned(self):
        if not os.path.exists(config.AASIST_DIR):
            print(f"[ModelLoader] AASIST repository not found. Cloning into {config.AASIST_DIR}...")
            try:
                subprocess.run(
                    ["git", "clone", config.AASIST_REPO_URL, config.AASIST_DIR],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                print("[ModelLoader] Successfully cloned AASIST repository.")
            except subprocess.CalledProcessError as e:
                raise ModelLoadError(f"Failed to clone AASIST repository: {e.stderr.decode()}")
        else:
            print("[ModelLoader] AASIST repository found.")

    def _ensure_weights_exist(self):
        if not os.path.exists(config.MODEL_WEIGHTS_PATH):
            raise ModelLoadError(
                f"Model weights not found at {config.MODEL_WEIGHTS_PATH}. "
                "The ClovaAI AASIST repository should contain this file by default. "
                "Please verify your repository state."
            )

    def _load_model(self):
        """Loads the AASIST model architecture and weights."""
        print("[ModelLoader] Loading AASIST model...")
        
        # Add AASIST repo to sys.path so we can import its modules
        if config.AASIST_DIR not in sys.path:
            sys.path.append(config.AASIST_DIR)
        
        try:
            from models.AASIST import Model
        except ImportError as e:
            raise ModelLoadError(f"Failed to import AASIST model architecture: {e}")

        # Load config
        if not os.path.exists(config.MODEL_CONFIG_PATH):
            raise ModelLoadError(f"Model config not found at {config.MODEL_CONFIG_PATH}")
            
        with open(config.MODEL_CONFIG_PATH, "r") as f:
            full_config = json.load(f)
            
        model_config = full_config["model_config"]
        
        # Initialize model
        try:
            self.model = Model(model_config).to(self.device)
            self.model.load_state_dict(torch.load(config.MODEL_WEIGHTS_PATH, map_location=self.device))
            self.model.eval()
            print("[ModelLoader] Model loaded successfully.")
        except Exception as e:
            raise ModelLoadError(f"Failed to load model weights: {e}")

    def predict(self, audio_tensor):
        """
        Runs inference on the audio tensor.
        audio_tensor: torch.Tensor of shape (N,) where N=64600
        Returns:
            probability of being genuine (float)
        """
        if self.model is None:
            raise RuntimeError("Model is not loaded. Call setup() first.")
            
        # AASIST expects input shape (batch_size, num_samples)
        # So we add a batch dimension
        if audio_tensor.dim() == 1:
            audio_tensor = audio_tensor.unsqueeze(0)
            
        audio_tensor = audio_tensor.to(self.device)
        
        with torch.no_grad():
            try:
                # Forward pass returns (last_hidden, output)
                _, output = self.model(audio_tensor)
                
                # output is (batch_size, 2)
                # Class 0 = Spoof, Class 1 = Bonafide
                probs = F.softmax(output, dim=1)
                
                # Extract the probability for class 1 (Bonafide/Genuine)
                genuine_prob = probs[0, 1].item()
                return genuine_prob
            except Exception as e:
                print(f"[ModelLoader] Inference error: {e}")
                raise e
