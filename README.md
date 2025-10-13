# 🛰️ NetLogger — Raspberry Pi Network Quality Logger

NetLogger is a lightweight, self-contained Python application that runs periodic network speed tests against **e& UAE (Etisalat)** and **du** servers, records results locally, and optionally pushes them to **Supabase** for remote analytics.

It is designed for **Raspberry Pi** devices deployed across locations to measure **QoS** metrics such as:
- Download / Upload throughput  
- Latency / Jitter (ping)  
- HTTP page-load time  
- Geo + ISP identification  

---

## 🚀 Features

- Multi-threaded **Speedtest CLI** runner (configurable threads per Pi model)
- **Auto-discovery and caching** of UAE-based Etisalat / du servers
- Periodic **ping**, **HTTP load**, and **geo-lookup** via ipinfo.io
- Local structured logs (CSV + TXT)
- Optional **Supabase REST push**
- Safe retry logic and clean **systemd service** integration

---

## 🧩 Directory Layout

| Path | Description |
|------|--------------|
| `/home/admin/netlogger/netlogger.py` | Main Python script |
| `/home/admin/netlogger/logs/` | Daily CSV / TXT logs |
| `/etc/systemd/system/netlogger.service` | Optional systemd unit |
| `/etc/netlogger.env` | Environment file (Supabase keys etc.) |
| `/home/admin/venvs/netlogger/` | Python virtual environment |

---

## ⚙️ Installation via `install_netlogger.sh`

Create an installer script called `install_netlogger.sh`:

```bash
#!/usr/bin/env bash
set -e

DEVICE_USER="admin"
APP_DIR="/home/${DEVICE_USER}/netlogger"

# -------- 1. SYSTEM PREPARATION --------
sudo apt update
sudo apt install -y python3-full python3-venv python3-pip git

# -------- 2. CREATE VENV --------
sudo -u ${DEVICE_USER} mkdir -p /home/${DEVICE_USER}/venvs
sudo -u ${DEVICE_USER} python3 -m venv /home/${DEVICE_USER}/venvs/netlogger
sudo -u ${DEVICE_USER} /home/${DEVICE_USER}/venvs/netlogger/bin/pip install --upgrade pip speedtest-cli requests

# -------- 3. FETCH LATEST CODE --------
REPO_URL="https://github.com/yourname/netlogger"
BRANCH="main"

echo "🌍 Fetching latest netlogger.py from GitHub..."
sudo -u ${DEVICE_USER} mkdir -p "${APP_DIR}"

if [ ! -d "${APP_DIR}/.git" ]; then
  sudo -u ${DEVICE_USER} git clone --depth 1 -b ${BRANCH} "${REPO_URL}" "${APP_DIR}"
else
  echo "🔄 Updating existing repository..."
  cd "${APP_DIR}"
  sudo -u ${DEVICE_USER} git pull origin ${BRANCH}
fi

# -------- 4. CREATE SYSTEMD SERVICE --------
cat <<'EOF' | sudo tee /etc/systemd/system/netlogger.service
[Unit]
Description=Network Logger (CSV + TXT + optional Supabase push)
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=admin
Group=admin
WorkingDirectory=/home/admin/netlogger
ExecStart=/home/admin/venvs/netlogger/bin/python -u /home/admin/netlogger/netlogger.py
EnvironmentFile=-/etc/netlogger.env
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable netlogger
sudo systemctl start netlogger

echo "✅ NetLogger installed and running!"
