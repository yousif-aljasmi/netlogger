#!/usr/bin/env bash
set -euo pipefail
# ==============================================
# NetLogger Full Installer (Environment-based)
# ==============================================

# -------- BASE CONFIG --------
DEVICE_USER="admin"
VENV_PATH="/home/${DEVICE_USER}/venvs/netlogger"
APP_DIR="/home/${DEVICE_USER}/netlogger"
SERVICE_FILE="/etc/systemd/system/netlogger.service"
ENV_FILE="/etc/netlogger.env"
PYTHON_BIN="/usr/bin/python3"
TIMEZONE="Asia/Dubai"

# -------- NETLOGGER VARIABLES --------
NETLOGGER_DEVICE_ID="NET-PI-xx"
NETLOGGER_INTERVAL_SECONDS="600"
NETLOGGER_PING_HOST="8.8.8.8"
NETLOGGER_PING_COUNT="5"
NETLOGGER_LOG_DIR="/home/admin/netlogger/logs"
NETLOGGER_SERVER_CACHE="/tmp/uae_servers_cache.json"
NETLOGGER_THREADS="4"

# -------- SUPABASE CONFIG --------
SUPABASE_URL="https://czgxoihuyapxoemgrron.supabase.co"
SUPABASE_ANON_KEY=""
SUPABASE_TABLE="netlogs"

# -------- UPDATE SOURCE (GitHub / Supabase) --------
UPDATE_SOURCE="github"   # set to "supabase" to use Supabase Storage
GITHUB_REPO_URL="https://github.com/yousif-aljasmi/netlogger"
GITHUB_BRANCH="main"
SUPABASE_CODE_URL="https://czgxoihuyapxoemgrron.supabase.co/storage/v1/object/public/netlogger/netlogger.py"

# ==============================================
# START INSTALLATION
# ==============================================

echo "📦 Updating system and installing dependencies..."
sudo apt update -y
sudo apt install -y python3-full python3-venv python3-pip git curl

# -------- TIMEZONE --------
echo "🕒 Setting timezone to ${TIMEZONE} ..."
sudo timedatectl set-timezone "${TIMEZONE}"

# -------- CREATE PYTHON VENV --------
echo "🐍 Creating Python virtual environment..."
sudo -u ${DEVICE_USER} mkdir -p "$(dirname ${VENV_PATH})"
sudo -u ${DEVICE_USER} ${PYTHON_BIN} -m venv "${VENV_PATH}"

echo "📦 Installing Python packages..."
source "${VENV_PATH}/bin/activate"
pip install --upgrade pip
pip install requests speedtest-cli numpy
deactivate

# -------- CREATE ENVIRONMENT FILE --------
echo "🔐 Creating environment file at ${ENV_FILE} ..."
sudo tee "${ENV_FILE}" >/dev/null <<EOF
# ========= NETLOGGER ENVIRONMENT VARIABLES =========

# --- Identity & Timing ---
NETLOGGER_DEVICE_ID=${NETLOGGER_DEVICE_ID}
NETLOGGER_INTERVAL_SECONDS=${NETLOGGER_INTERVAL_SECONDS}

# --- Ping Settings ---
NETLOGGER_PING_HOST=${NETLOGGER_PING_HOST}
NETLOGGER_PING_COUNT=${NETLOGGER_PING_COUNT}

# --- Paths ---
NETLOGGER_LOG_DIR=${NETLOGGER_LOG_DIR}
NETLOGGER_SERVER_CACHE=${NETLOGGER_SERVER_CACHE}

# --- Speedtest Threads ---
NETLOGGER_THREADS=${NETLOGGER_THREADS}

# --- Supabase Configuration ---
SUPABASE_URL=${SUPABASE_URL}
SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
SUPABASE_TABLE=${SUPABASE_TABLE}

EOF

sudo chmod 600 "${ENV_FILE}"

# -------- PREPARE APPLICATION DIRECTORY --------
echo "📁 Preparing application directory..."
sudo -u ${DEVICE_USER} mkdir -p "${APP_DIR}/logs"

# -------- FETCH LATEST CODE --------
echo "🌍 Fetching latest netlogger.py code (${UPDATE_SOURCE})..."

if [[ "${UPDATE_SOURCE}" == "github" ]]; then
    if [ ! -d "${APP_DIR}/.git" ]; then
        echo "📥 Cloning from GitHub: ${GITHUB_REPO_URL} (${GITHUB_BRANCH})"
        sudo -u ${DEVICE_USER} git clone --depth 1 -b ${GITHUB_BRANCH} "${GITHUB_REPO_URL}" "${APP_DIR}"
    else
        echo "🔄 Updating existing GitHub repo..."
        cd "${APP_DIR}"
        sudo -u ${DEVICE_USER} git pull origin ${GITHUB_BRANCH}
    fi
elif [[ "${UPDATE_SOURCE}" == "supabase" ]]; then
    echo "📥 Downloading from Supabase Storage..."
    sudo -u ${DEVICE_USER} curl -L -o "${APP_DIR}/netlogger.py" "${SUPABASE_CODE_URL}"
else
    echo "❌ Invalid UPDATE_SOURCE value. Use 'github' or 'supabase'."
    exit 1
fi

sudo chown -R ${DEVICE_USER}:${DEVICE_USER} "${APP_DIR}"
sudo chmod -R 775 "${APP_DIR}"

# -------- SYSTEMD SERVICE CREATION --------
echo "⚙️ Creating systemd service..."
sudo tee "${SERVICE_FILE}" >/dev/null <<EOF
[Unit]
Description=Network Logger (CSV + TXT + optional Supabase push)
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=${DEVICE_USER}
Group=${DEVICE_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${VENV_PATH}/bin/python -u ${APP_DIR}/netlogger.py
EnvironmentFile=-${ENV_FILE}
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# -------- ENABLE & START SERVICE --------
echo "🚀 Enabling and starting netlogger service..."
sudo systemctl daemon-reload
sudo systemctl enable netlogger
sudo systemctl restart netlogger

# -------- SUMMARY --------
echo ""
echo "✅ NetLogger installation complete!"
echo "----------------------------------------"
echo "🟢 Service status: sudo systemctl status netlogger"
echo "📄 Logs directory: ${NETLOGGER_LOG_DIR}"
echo "⚙️ Env file:       ${ENV_FILE}"
echo "🌐 Update source:  ${UPDATE_SOURCE}"
echo "----------------------------------------"
echo "To update code later, re-run this script."
