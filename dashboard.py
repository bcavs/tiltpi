#!/usr/bin/env python3
"""Tilt Hydrometer Web Dashboard."""

import csv
import io
from datetime import date
from flask import Flask, jsonify, render_template, request, Response, send_file

import db

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/readings")
def readings():
    brew_id = request.args.get("brew_id", type=int)
    if brew_id:
        data = db.get_readings(brew_id)
    else:
        data = db.get_readings_for_active_brew()
    return jsonify(data if data else [])


@app.route("/api/config", methods=["GET"])
def get_config():
    brew = db.get_active_brew()
    if not brew:
        return jsonify({"brew_name": "", "target_fg": 1.010, "temp_low": 60, "temp_high": 75})
    return jsonify({
        "brew_name": brew["name"],
        "target_fg": brew["target_fg"],
        "temp_low": brew["temp_low"],
        "temp_high": brew["temp_high"],
    })


@app.route("/api/config", methods=["POST"])
def update_config():
    brew = db.get_active_brew()
    if not brew:
        return jsonify({"error": "No active brew"}), 404
    data = request.get_json()
    fields = {}
    if "brew_name" in data:
        fields["name"] = str(data["brew_name"])
    if "target_fg" in data:
        fields["target_fg"] = float(data["target_fg"])
    if "temp_low" in data:
        fields["temp_low"] = float(data["temp_low"])
    if "temp_high" in data:
        fields["temp_high"] = float(data["temp_high"])
    db.update_brew(brew["id"], **fields)
    return get_config()


@app.route("/api/export.csv")
def export_csv():
    brew_id = request.args.get("brew_id", type=int)
    if brew_id:
        brew = db.get_brew(brew_id)
        data = db.get_readings(brew_id)
    else:
        brew = db.get_active_brew()
        data = db.get_readings_for_active_brew()

    if not data:
        return Response("No data", status=404)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["timestamp", "color", "temp_f", "temp_c", "gravity"])
    writer.writeheader()
    writer.writerows(data)

    filename = (brew.get("name", "").replace(" ", "_") if brew else "") or "tilt_log"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
    )


@app.route("/api/brews")
def list_brews():
    return jsonify(db.list_brews())


@app.route("/api/brews/<int:brew_id>/readings")
def brew_readings(brew_id):
    return jsonify(db.get_readings(brew_id))


@app.route("/api/brews/start", methods=["POST"])
def start_brew():
    active = db.get_active_brew()
    if active:
        db.end_brew(active["id"])
    data = request.get_json() or {}
    brew_id = db.create_brew(
        color=data.get("color", ""),
        name=data.get("name", ""),
        target_fg=data.get("target_fg", 1.010),
        temp_low=data.get("temp_low", 60),
        temp_high=data.get("temp_high", 75),
    )
    return jsonify(db.get_brew(brew_id)), 201


@app.route("/api/brews/<int:brew_id>", methods=["PATCH"])
def update_brew(brew_id):
    brew = db.get_brew(brew_id)
    if not brew:
        return jsonify({"error": "Brew not found"}), 404
    data = request.get_json() or {}
    fields = {}
    if "name" in data:
        fields["name"] = str(data["name"])
    db.update_brew(brew_id, **fields)
    return jsonify(db.get_brew(brew_id))


@app.route("/api/brews/<int:brew_id>/end", methods=["POST"])
def end_brew(brew_id):
    db.end_brew(brew_id)
    return jsonify(db.get_brew(brew_id))


@app.route("/api/brews/<int:brew_id>", methods=["DELETE"])
def delete_brew(brew_id):
    brew = db.get_brew(brew_id)
    if not brew:
        return jsonify({"error": "Brew not found"}), 404
    db.delete_brew(brew_id)
    return jsonify({"ok": True})


@app.route("/api/backup.db")
def backup_db():
    return send_file(
        db.DB_PATH,
        mimetype="application/x-sqlite3",
        as_attachment=True,
        download_name=f"tiltpi-backup-{date.today()}.db",
    )


if __name__ == "__main__":
    db.init_db()
    db.migrate_from_json()
    app.run(host="0.0.0.0", port=8080)
