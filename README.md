# 🛰️ NetLogger — Network Quality Logger for Raspberry Pi / Linux VM

**NetLogger** is a lightweight network quality monitoring tool that:
- Runs scheduled speed tests to **Etisalat (e& UAE)** and **du (EITC)** servers.  
- Logs results locally (CSV + TXT).  
- Optionally pushes results to **Supabase** cloud database.  
- Runs automatically as a **systemd service**.  
- Fully configurable through a `.env` file — no code editing required.

---

## 📁 Architecture Overview

| Component | Description |
|------------|--------------|
| `netlogger.py` | Main Python application |
| `/etc/netlogger.env` | Environment variables controlling behavior |
| `/home/admin/netlogger/` | App directory (code + logs) |
| `/home/admin/venvs/netlogger/` | Python virtual environment |
| `/etc/systemd/system/netlogger.service` | Service definition |
| `install_netlogger.sh` | Auto installer and updater |

---

## ⚙️ Requirements

- Ubuntu / Debian / Raspberry Pi OS / RHEL 9-compatible Linux  
- Python 3.9 or higher  
- Internet connectivity (for speedtest + Supabase push)  

---

## 🚀 Installation (One Command)

Clone the repository and run the installer:

```bash
git clone https://github.com/yourname/netlogger.git
cd netlogger
sudo chmod +x install_netlogger.sh
sudo ./install_netlogger.sh
```

The installer will:

1. Update system packages  
2. Install Python and dependencies  
3. Create a Python virtual environment  
4. Create `/etc/netlogger.env` with your configuration  
5. Fetch the latest `netlogger.py` (from GitHub or Supabase)  
6. Create and start the `netlogger.service`  

---

## 🔐 Environment Configuration

All configuration is controlled through `/etc/netlogger.env`.  
The installer automatically creates this file, but you can edit it later to adjust settings.

### 📄 Example: `/etc/netlogger.env`

```bash
# ========= NETLOGGER ENVIRONMENT VARIABLES =========

# --- Identity & Timing ---
NETLOGGER_DEVICE_ID=NET-PI-01              # Unique ID per device
NETLOGGER_INTERVAL_SECONDS=600             # Interval between tests (seconds)

# --- Ping Settings ---
NETLOGGER_PING_HOST=8.8.8.8
NETLOGGER_PING_COUNT=5

# --- Paths ---
NETLOGGER_LOG_DIR=/home/admin/netlogger/logs
NETLOGGER_SERVER_CACHE=/tmp/uae_servers_cache.json

# --- Speedtest Threads ---
# Recommended: 2 (Pi 3), 4 (Pi 4), 6–8 (Pi 5 or VM)
NETLOGGER_THREADS=4

# --- Supabase Configuration ---
SUPABASE_URL=https://czgxoihuyapxoemgrron.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_TABLE=netlogs
```

---

## 🧩 Service Management

Once installed, the service runs automatically on startup.

| Action | Command |
|--------|----------|
| Start service | `sudo systemctl start netlogger` |
| Stop service | `sudo systemctl stop netlogger` |
| Restart service | `sudo systemctl restart netlogger` |
| Enable on boot | `sudo systemctl enable netlogger` |
| Check status | `sudo systemctl status netlogger` |
| View live logs | `journalctl -u netlogger -f` |

---

## 🗂️ Output Files

| File | Purpose |
|------|----------|
| `/home/admin/netlogger/logs/logs_YYYY-MM-DD.csv` | CSV data (structured for analytics) |
| `/home/admin/netlogger/logs/logs_YYYY-MM-DD.txt` | Text summary log for quick viewing |
| `/tmp/uae_servers_cache.json` | Cached list of UAE servers (auto-refreshed) |

---

## 🌐 Supabase Integration

The application automatically posts results to your Supabase table (e.g. `netlogs`)
whenever valid credentials are present in `/etc/netlogger.env`.

To disable cloud upload:

```bash
sudo sed -i '/SUPABASE_URL/d;/SUPABASE_ANON_KEY/d' /etc/netlogger.env
sudo systemctl restart netlogger
```

---

## 🔄 Updating the Code

### 1️⃣ Update from GitHub (Default)
```bash
cd /home/admin/netlogger
sudo git pull origin main
sudo systemctl restart netlogger
```

### 2️⃣ Update from Supabase Storage
If your script is set to pull from Supabase (see `install_netlogger.sh`):
```bash
sudo ./install_netlogger.sh
```

---

## ⚙️ Manual Reinstall (if needed)

```bash
sudo systemctl stop netlogger
sudo rm -rf /home/admin/netlogger /home/admin/venvs/netlogger /etc/netlogger.env /etc/systemd/system/netlogger.service
sudo ./install_netlogger.sh
```

---

## 🧰 Troubleshooting

| Symptom | Possible Cause | Fix |
|----------|----------------|-----|
| `speedtest.ConfigRetrievalError` | Speedtest.net blocked or misconfigured | Wait 30 s — script retries automatically |
| `[Supabase] 401 Unauthorized` | Invalid Supabase key or URL | Check `/etc/netlogger.env` credentials |
| Logs not appearing | Wrong log path | Ensure `NETLOGGER_LOG_DIR` directory exists |
| Service not starting | Missing Python venv or permissions | Re-run `install_netlogger.sh` |
| High CPU | Too many threads | Lower `NETLOGGER_THREADS` in `.env` |

---

## 📊 Example Output

**CSV Sample:**
```csv
ts_iso,device,hostname,local_ip,public_ip,city,region,country,lat,lon,isp,test_id,target_isp,speedtest_server,speedtest_sponsor,speedtest_country,server_id,latency_ms,download_mbps,upload_mbps,duration_s,threads_used,rtt_ms,jitter_ms,http_load_s
2025-10-13T10:30:12+04:00,NET-PI-01,netpi04,192.168.1.50,83.110.xx.xx,Dubai,DU,UAE,25.20,55.27,e& UAE,97a9...,Etisalat,Alain,e& UAE,UAE,34239,15.3,225.7,38.1,31.2,4,20.4,2.3,0.8
```

**TXT Sample:**
```
[2025-10-13T10:30:12+04:00] ✅ ETISALAT ↓225.7 ↑38.1 Mbps (dur 31.2 s)
[2025-10-13T10:41:32+04:00] ✅ DU ↓210.4 ↑35.9 Mbps (dur 30.8 s)
```

---

## 🧩 Credits

Developed by **Yousif Ali Al Jasmi**  
Manager – Telecom Data Analysis / Big Data & AI / Technology Development Affairs  
**TDRA – UAE**

---

## 📄 License

MIT License © 2025 Yousif Ali Al Jasmi
