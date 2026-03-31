#!/usr/bin/env python3
"""Tilt Hydrometer Web Dashboard."""

import csv
import io
import json
import os
from flask import Flask, jsonify, render_template, request, Response

app = Flask(__name__)
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
LOG_FILE = os.path.join(DATA_DIR, "tilt_log.json")
CONFIG_FILE = os.path.join(DATA_DIR, "brew_config.json")

DEFAULT_CONFIG = {
    "brew_name": "",
    "target_fg": 1.010,
    "temp_low": 60,
    "temp_high": 75,
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def save_config(config):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/readings")
def readings():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            return jsonify(json.load(f))
    return jsonify([])


@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(load_config())


@app.route("/api/config", methods=["POST"])
def update_config():
    config = load_config()
    data = request.get_json()
    if "brew_name" in data:
        config["brew_name"] = str(data["brew_name"])
    if "target_fg" in data:
        config["target_fg"] = float(data["target_fg"])
    if "temp_low" in data:
        config["temp_low"] = float(data["temp_low"])
    if "temp_high" in data:
        config["temp_high"] = float(data["temp_high"])
    save_config(config)
    return jsonify(config)


@app.route("/api/export.csv")
def export_csv():
    if not os.path.exists(LOG_FILE):
        return Response("No data", status=404)
    with open(LOG_FILE) as f:
        data = json.load(f)
    if not data:
        return Response("No data", status=404)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["timestamp", "color", "temp_f", "temp_c", "gravity"])
    writer.writeheader()
    writer.writerows(data)

    config = load_config()
    filename = config.get("brew_name", "").replace(" ", "_") or "tilt_log"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
