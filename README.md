# 🛰️ NetLogger — Raspberry Pi Network Quality Logger

NetLogger is a **lightweight autonomous network measurement agent** designed for **Raspberry Pi** devices.  
It performs **scheduled speed tests**, **ping/jitter measurements**, and **HTTP load checks**, logs the data locally (CSV + TXT), and optionally pushes them to a **Supabase** backend for centralized analytics.

---

## 🚀 Key Features

- 📡 Dual-ISP testing: **Etisalat (e& UAE)** and **du**
- ⚙️ Auto-discovery and caching of UAE-based speedtest servers  
- 🔁 Scheduled tests every `INTERVAL_SECONDS`
- 🌍 Geo + public IP detection via `ipinfo.io`
- 💾 Local CSV/TXT logging
- ☁️ Optional push to Supabase REST API
- 🧵 Multi-threaded throughput testing (`THREADS` auto-optimized)
- 🧠 Graceful restart and systemd service integration
- 🔄 Auto-update from **GitHub** or **Supabase storage**

---

## 📦 Automated Installer

This repository includes a one-shot **bash installer**:  
`install_netlogger.sh`  
which handles everything — dependencies, venv, environment variables, code fetch, and service setup.

### ✅ What It Does

| Step | Action |
|------|--------|
| 1️⃣ | Installs `python3`, `pip`, `venv`, `git`, `curl` |
| 2️⃣ | Creates a virtual environment (`/home/admin/venvs/netlogger`) |
| 3️⃣ | Installs Python dependencies: `requests`, `speedtest-cli`, `numpy` |
| 4️⃣ | Configures system timezone (`Asia/Dubai`) |
| 5️⃣ | Writes `/etc/netlogger.env` with Supabase credentials |
| 6️⃣ | Fetches latest code (from **GitHub** or **Supabase**) |
| 7️⃣ | Creates and enables a **systemd** service |
| 8️⃣ | Starts the service automatically |

---

## 🧰 Installation Steps

```bash
# Clone or download the installer
curl -L -o install_netlogger.sh https://raw.githubusercontent.com/yousif-aljasmi/netlogger/main/install_netlogger.sh
chmod +x install_netlogger.sh

# Run the installer
sudo ./install_netlogger.sh
