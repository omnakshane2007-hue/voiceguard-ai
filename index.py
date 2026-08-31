import os
import traceback
from flask import Flask, Response, send_from_directory

app = Flask(__name__)

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route("/")
def index():
    try:
        html_path = os.path.join(ROOT_DIR, "index.html")
        if not os.path.exists(html_path):
            html_path = os.path.join(ROOT_DIR, "templates", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/html")
    except Exception as e:
        return f"Error: {e}\n\n{traceback.format_exc()}", 500

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(os.path.join(ROOT_DIR, "static"), filename)
