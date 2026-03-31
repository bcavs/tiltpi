#!/bin/bash
# Run this on the Pi to install services
set -e

sudo cp systemd/tilt-monitor.service /etc/systemd/system/
sudo cp systemd/tilt-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tilt-monitor tilt-dashboard
sudo systemctl start tilt-monitor tilt-dashboard
sudo systemctl status tilt-monitor tilt-dashboard
