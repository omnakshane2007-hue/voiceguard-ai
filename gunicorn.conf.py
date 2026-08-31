"""
Gunicorn configuration for VOICEGUARD AI on Railway.

Design decisions:
- 1 worker: AASIST (~1.2MB) + RawNet2 (~67MB) PyTorch models are loaded
  once per worker. More workers = OOM on Railway's 512MB–1GB plans.
- 4 threads: handles concurrent audio analysis requests without duplicating
  the model in memory.
- 120s timeout: Gemini API + AASIST + RawNet2 can take 10-30s per chunk.
  We need enough headroom for all three in parallel.
"""

import multiprocessing
import os

# ── Binding ────────────────────────────────────────────────────────────────
port = os.environ.get("PORT", "8000")
bind = f"0.0.0.0:{port}"

# ── Worker model ───────────────────────────────────────────────────────────
# Single process, multi-threaded: keeps model memory footprint small.
workers = 1
threads = 4
worker_class = "gthread"

# ── Timeouts ──────────────────────────────────────────────────────────────
timeout = 120          # AI inference can take up to 30s; Gunicorn kills after this
graceful_timeout = 30  # allow in-flight requests to complete on SIGTERM
keepalive = 5

# ── Logging ────────────────────────────────────────────────────────────────
loglevel = "info"
accesslog = "-"   # stdout
errorlog = "-"    # stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" %(D)sμs'

# ── Process name ──────────────────────────────────────────────────────────
proc_name = "voiceguard-ai"
