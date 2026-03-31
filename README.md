# TiltPi

A lightweight Tilt Hydrometer monitor and web dashboard for Raspberry Pi. Reads BLE iBeacon data from [Tilt Hydrometers](https://tilthydrometer.com/) and displays real-time gravity and temperature charts in a web dashboard.

## Features

- Scans for all Tilt Hydrometer colors (Red, Green, Black, Purple, Orange, Blue, Yellow, Pink)
- Logs specific gravity and temperature (°F/°C) to JSON
- Web dashboard with live-updating charts (auto-refreshes every 5 seconds)
- Runs as systemd services (auto-starts on boot)
- Optional Cloudflare Tunnel for remote access

## Requirements

- Raspberry Pi 3/4/5 (or any Linux device with Bluetooth LE)
- Python 3
- `bluez` (usually pre-installed on Raspberry Pi OS / Debian)

## Setup

### 1. Clone and install dependencies

```bash
cd ~/Desktop/tilt-monitor  # or wherever you want it
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```

### 2. Test manually

Run the BLE monitor (requires sudo for Bluetooth access):

```bash
sudo venv/bin/python tilt_monitor.py
```

Run the dashboard in a separate terminal:

```bash
. venv/bin/activate
python dashboard.py
```

Visit `http://<your-pi-ip>:8080` to see the dashboard.

### 3. Generate test data (optional)

If you don't have a Tilt nearby, generate dummy fermentation data:

```bash
. venv/bin/activate
python generate_dummy_data.py
```

### 4. Install as services

This sets up both the monitor and dashboard to run on boot:

```bash
chmod +x setup.sh
./setup.sh
```

Manage the services with:

```bash
sudo systemctl status tilt-monitor tilt-dashboard
sudo systemctl stop tilt-monitor
sudo systemctl start tilt-monitor
sudo systemctl restart tilt-dashboard
```

View logs:

```bash
journalctl -u tilt-monitor -f
journalctl -u tilt-dashboard -f
```

## Remote Access with Cloudflare Tunnel

To access the dashboard from anywhere:

### 1. Install cloudflared

```bash
sudo curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -o /usr/local/bin/cloudflared
sudo chmod +x /usr/local/bin/cloudflared
```

### 2. Authenticate and create the tunnel

```bash
cloudflared tunnel login
cloudflared tunnel create tilt
cloudflared tunnel route dns tilt tilt.yourdomain.com
```

### 3. Configure the tunnel

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: tilt
credentials-file: /home/<user>/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: tilt.yourdomain.com
    service: http://localhost:8080
  - service: http_status:404
```

Replace `<user>` and `<TUNNEL_ID>` with your values. Find the tunnel ID with `cloudflared tunnel list`.

### 4. Install as a service

```bash
sudo mkdir -p /etc/cloudflared
sudo cp ~/.cloudflared/config.yml /etc/cloudflared/
sudo cp ~/.cloudflared/*.json /etc/cloudflared/
```

Edit `/etc/cloudflared/config.yml` to update the credentials path to `/etc/cloudflared/<TUNNEL_ID>.json`, then:

```bash
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

Manage the tunnel:

```bash
sudo systemctl stop cloudflared    # turn off
sudo systemctl start cloudflared   # turn on
sudo systemctl disable cloudflared # disable on boot
sudo systemctl enable cloudflared  # enable on boot
```

## Project Structure

```
├── tilt_monitor.py          # BLE scanner - reads Tilt iBeacon data
├── dashboard.py             # Flask web dashboard
├── generate_dummy_data.py   # Generate test data for the dashboard
├── requirements.txt         # Python dependencies
├── setup.sh                 # Install systemd services
├── systemd/
│   ├── tilt-monitor.service
│   └── tilt-dashboard.service
└── data/                    # Created at runtime
    └── tilt_log.json        # Reading log (last 1000 entries)
```
