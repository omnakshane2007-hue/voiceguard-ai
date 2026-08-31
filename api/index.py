import os
import sys
import traceback
from flask import Flask, Response

app = Flask(__name__)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

def find_index_html():
    search_paths = [
        os.path.join(CURRENT_DIR, "index.html"),
        os.path.join(PARENT_DIR, "index.html"),
        os.path.join(PARENT_DIR, "templates", "index.html"),
        os.path.join(CURRENT_DIR, "templates", "index.html"),
        "/var/task/templates/index.html",
        "/var/task/index.html",
    ]
    for p in search_paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
    return None

@app.route("/")
def index():
    try:
        content = find_index_html()
        if content:
            return Response(content, mimetype="text/html")
        return f"Index HTML not found. Scanned paths: cwd={os.getcwd()}, dir={CURRENT_DIR}, files={os.listdir(PARENT_DIR) if os.path.exists(PARENT_DIR) else 'no parent'}", 500
    except Exception as e:
        return f"Error: {e}\n\n{traceback.format_exc()}", 500

@app.route("/static/<path:path>")
def serve_static(path):
    try:
        search_paths = [
            os.path.join(CURRENT_DIR, "static", path),
            os.path.join(PARENT_DIR, "static", path),
            f"/var/task/static/{path}",
        ]
        for p in search_paths:
            if os.path.exists(p):
                with open(p, "rb") as f:
                    data = f.read()
                mime = "application/javascript" if path.endswith(".js") else "text/css" if path.endswith(".css") else "application/octet-stream"
                return Response(data, mimetype=mime)
        return f"Static file {path} not found", 404
    except Exception as e:
        return f"Error: {e}\n\n{traceback.format_exc()}", 500
