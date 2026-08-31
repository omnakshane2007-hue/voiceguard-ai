import os
import sys

# Ensure root directory is on the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app

# Vercel serverless function entrypoint
app = app
