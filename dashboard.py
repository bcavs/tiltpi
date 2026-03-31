#!/usr/bin/env python3
"""Tilt Hydrometer Web Dashboard."""

import json
import os
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
LOG_FILE = os.path.join(DATA_DIR, "tilt_log.json")

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tilt Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0f1117; color: #e0e0e0; }
        .header { padding: 24px; text-align: center; border-bottom: 1px solid #1e2130; }
        .header h1 { font-size: 1.5rem; font-weight: 600; }
        .header .sub { color: #888; font-size: 0.85rem; margin-top: 4px; }
        .cards { display: flex; gap: 16px; padding: 24px; justify-content: center; flex-wrap: wrap; }
        .card {
            background: #181a24; border: 1px solid #1e2130; border-radius: 12px;
            padding: 24px; min-width: 180px; text-align: center;
        }
        .card .label { color: #888; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }
        .card .value { font-size: 2rem; font-weight: 700; margin-top: 8px; }
        .card .unit { color: #888; font-size: 0.9rem; }
        .gravity .value { color: #60a5fa; }
        .temp .value { color: #f97316; }
        .status .value { color: #34d399; font-size: 1rem; }
        .chart-container { padding: 8px 24px 24px; }
        canvas { background: #181a24; border-radius: 12px; border: 1px solid #1e2130; }
        .no-data { text-align: center; padding: 80px 24px; color: #555; font-size: 1.1rem; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Tilt Hydrometer</h1>
        <div class="sub" id="last-updated">Waiting for data...</div>
    </div>
    <div id="content" class="no-data">No readings yet. Make sure the Tilt monitor is running.</div>

    <script>
    let gravityChart, tempChart;

    function initCharts(container) {
        container.innerHTML = `
            <div class="cards">
                <div class="card gravity">
                    <div class="label">Specific Gravity</div>
                    <div class="value" id="sg">--</div>
                </div>
                <div class="card temp">
                    <div class="label">Temperature</div>
                    <div class="value" id="temp">--</div>
                    <div class="unit" id="temp-unit"></div>
                </div>
                <div class="card status">
                    <div class="label">Tilt Color</div>
                    <div class="value" id="color">--</div>
                </div>
            </div>
            <div class="chart-container"><canvas id="gravityChart" height="120"></canvas></div>
            <div class="chart-container"><canvas id="tempChart" height="120"></canvas></div>
        `;

        const opts = (label, color) => ({
            responsive: true,
            plugins: { legend: { display: false },
                title: { display: true, text: label, color: '#888', font: { size: 14 } } },
            scales: {
                x: { ticks: { color: '#555', maxTicksLimit: 8 }, grid: { color: '#1e2130' } },
                y: { ticks: { color: '#888' }, grid: { color: '#1e2130' } }
            }
        });

        gravityChart = new Chart(document.getElementById('gravityChart'), {
            type: 'line',
            data: { labels: [], datasets: [{ data: [], borderColor: '#60a5fa', borderWidth: 2, pointRadius: 0, fill: false }] },
            options: opts('Specific Gravity', '#60a5fa')
        });

        tempChart = new Chart(document.getElementById('tempChart'), {
            type: 'line',
            data: { labels: [], datasets: [{ data: [], borderColor: '#f97316', borderWidth: 2, pointRadius: 0, fill: false }] },
            options: opts('Temperature (°F)', '#f97316')
        });
    }

    async function fetchData() {
        try {
            const res = await fetch('/api/readings');
            const data = await res.json();
            if (!data.length) return;

            const content = document.getElementById('content');
            if (!gravityChart) initCharts(content);

            const latest = data[data.length - 1];
            document.getElementById('sg').textContent = latest.gravity.toFixed(3);
            document.getElementById('temp').textContent = `${latest.temp_f}°F`;
            document.getElementById('temp-unit').textContent = `${latest.temp_c}°C`;
            document.getElementById('color').textContent = latest.color;
            document.getElementById('last-updated').textContent = `Last reading: ${new Date(latest.timestamp).toLocaleString()}`;

            const labels = data.map(r => new Date(r.timestamp).toLocaleTimeString());
            gravityChart.data.labels = labels;
            gravityChart.data.datasets[0].data = data.map(r => r.gravity);
            gravityChart.update('none');

            tempChart.data.labels = labels;
            tempChart.data.datasets[0].data = data.map(r => r.temp_f);
            tempChart.update('none');
        } catch(e) {}
    }

    fetchData();
    setInterval(fetchData, 5000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/readings')
def readings():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            return jsonify(json.load(f))
    return jsonify([])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
