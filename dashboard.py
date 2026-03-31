#!/usr/bin/env python3
"""Tilt Hydrometer Web Dashboard."""

import json
import os
from flask import Flask, jsonify, render_template

app = Flask(__name__)
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
LOG_FILE = os.path.join(DATA_DIR, "tilt_log.json")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/readings")
def readings():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            return jsonify(json.load(f))
    return jsonify([])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
