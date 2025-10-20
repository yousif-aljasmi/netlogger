#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Network logger for Raspberry Pi / VM
------------------------------------
Runs scheduled speed tests against e& UAE (Etisalat) and du servers,
logs metrics locally (CSV + TXT) and optionally pushes to Supabase.
All configuration is read from environment variables.
"""

import os, sys, time, csv, json, socket, statistics, signal, uuid, random, traceback, requests
from datetime import datetime, timezone

# ========= CONFIGURATION (read from environment) =========

DEVICE_ID         = os.getenv("NETLOGGER_DEVICE_ID", "NET-PI-xx")
INTERVAL_SECONDS  = int(os.getenv("NETLOGGER_INTERVAL_SECONDS", "600"))
PING_HOST         = os.getenv("NETLOGGER_PING_HOST", "8.8.8.8")
PING_COUNT        = int(os.getenv("NETLOGGER_PING_COUNT", "5"))
LOG_DIR           = os.getenv("NETLOGGER_LOG_DIR", "/home/admin/netlogger/logs")
SERVER_CACHE_FILE = os.getenv("NETLOGGER_SERVER_CACHE", "/tmp/uae_servers_cache.json")

LAST_GOOD_FILE = "/tmp/last_good_server.json"

def load_last_good():
    try:
        if os.path.exists(LAST_GOOD_FILE):
            with open(LAST_GOOD_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_last_good(isp, server_info):
    try:
        data = load_last_good()
        data[isp] = server_info
        with open(LAST_GOOD_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

# Thread count for Speedtest
THREADS = int(os.getenv("NETLOGGER_THREADS", str(min(4, os.cpu_count() or 4))))

# Supabase configuration
SUPABASE_URL      = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_TABLE    = os.getenv("SUPABASE_TABLE", "netlogs")

os.makedirs(LOG_DIR, exist_ok=True)

# ========= SAFE SPEEDTEST CONSTRUCTOR =========
def safe_speedtest(timeout=120):
    import speedtest
    for attempt in range(3):
        try:
            st = speedtest.Speedtest(timeout=timeout)
            return st
        except speedtest.ConfigRetrievalError as e:
            if "403" in str(e):
                print(f"⚠️ 403 from speedtest config — retrying ({attempt+1}/3)")
                time.sleep(30)
                continue
            raise
        except Exception as e:
            print(f"⚠️ Speedtest init error: {e}")
            time.sleep(10)
    raise RuntimeError("Speedtest configuration failed after 3 retries.")

# ========= GEO/IP =========
_GEO_CACHE = {"ts": 0.0, "data": None}
def get_ipinfo():
    now = time.time()
    if _GEO_CACHE["data"] and (now - _GEO_CACHE["ts"] < 1800):
        return _GEO_CACHE["data"]
    try:
        r = requests.get("https://ipinfo.io/json", timeout=6)
        j = r.json()
        lat, lon = (j.get("loc", "") + ",").split(",")[:2]
        data = {
            "public_ip": j.get("ip"), "city": j.get("city"), "region": j.get("region"),
            "country": j.get("country"), "lat": lat, "lon": lon, "isp": j.get("org"),
        }
        _GEO_CACHE.update({"ts": now, "data": data})
        return data
    except Exception:
        return {"public_ip": None, "city": None, "region": None,
                "country": None, "lat": None, "lon": None, "isp": None}

# ========= HELPERS =========
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None

def run_ping(host=PING_HOST, count=PING_COUNT):
    import subprocess
    try:
        p = subprocess.run(["ping", "-n", "-c", str(count), "-W", "1", host],
                           capture_output=True, text=True)
        times = [float(line.split("time=")[1].split(" ")[0])
                 for line in p.stdout.splitlines() if "time=" in line]
        if not times:
            return None, None
        return round(sum(times)/len(times), 2), round(statistics.pstdev(times), 2)
    except Exception:
        return None, None

def measure_http_load(url="https://www.bbc.com/"):
    try:
        t0 = time.perf_counter()
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return round(time.perf_counter() - t0, 2)
    except Exception:
        return None

# ========= SERVER CACHE =========
def load_cached_servers():
    try:
        if not os.path.exists(SERVER_CACHE_FILE):
            return None
        with open(SERVER_CACHE_FILE) as f:
            data = json.load(f)
        def _ok(lst):
            out = []
            for s in lst or []:
                try:
                    sid = int(str(s.get("id")).strip())
                    if sid >= 1000:
                        out.append({
                            "id": sid,
                            "sponsor": s.get("sponsor"),
                            "name": s.get("name"),
                            "country": s.get("country")
                        })
                except:
                    pass
            return out
        e = _ok(data.get("etisalat"))
        d = _ok(data.get("du"))
        if not e or not d:
            return None
        return {"etisalat": e, "du": d}
    except Exception:
        return None

def save_cached_servers(data):
    try:
        open(SERVER_CACHE_FILE, "w").write(json.dumps(data))
    except Exception:
        pass

# ========= DISCOVER SERVERS =========
def discover_servers():
    cached = load_cached_servers()
    if cached:
        return cached
    print("🔍 Discovering UAE servers…")
    try:
        import speedtest
        st = safe_speedtest()
        servers = st.get_servers()
        et, du = [], []
        for server_list in servers.values():
            for s in server_list:
                c = (s.get("country") or "").lower()
                sp = (s.get("sponsor") or "").lower()
                nm = (s.get("name") or "").lower()
                if not any(k in c for k in ["united arab", "uae", "u.a.e"]):
                    continue
                sid = int(str(s["id"]))
                info = {"id": sid, "sponsor": s.get("sponsor"),
                        "name": s.get("name"), "country": s.get("country")}
                if any(k in sp or k in nm for k in ["e&", "etisalat", "emirates tele"]):
                    et.append(info)
                elif any(k in sp or k in nm for k in ["du", "eitc"]):
                    du.append(info)
        if not et:
            et = [{"id": 34239, "sponsor": "e& UAE", "name": "Alain", "country": "UAE"}]
        if not du:
            du = [{"id": 1692, "sponsor": "du", "name": "Abu Dhabi", "country": "UAE"}]
        print(f"✅ Found {len(et)} Etisalat and {len(du)} du servers")
        data = {"etisalat": et, "du": du}
        save_cached_servers(data)
        return data
    except Exception as e:
        print(f"[discover] failed: {e}")
        return {"etisalat": [], "du": []}

# ========= SPEEDTEST RUNNER =========
def run_speedtest_dynamic(target, retries=2):
    import speedtest
    servers = discover_servers()
    cand = servers.get(target, [])
    if not cand:
        print(f"⚠️ No {target} servers found — triggering rediscovery")
        save_cached_servers({"etisalat": [], "du": []})
        time.sleep(3)
        servers = discover_servers()
        cand = servers.get(target, [])
    
    # Try last known good server first if available
    last_good = load_last_good().get(target)
    if last_good:
        print(f"💾 Using last known good {target.upper()} server first: "
              f"{last_good['name']} ({last_good['sponsor']}) [id={last_good['id']}]")
        cand = [last_good] + [c for c in cand if c["id"] != last_good["id"]]
    
    random.shuffle(cand)
    failure_count = 0


    for ch in cand[:3]:
        for a in range(1, retries + 1):
            print(f"🚀 {target.upper()} → {ch['name']} ({ch['sponsor']}) [id={ch['id']}] try {a}")
            try:
                st = safe_speedtest(timeout=180)  # ⏱️ slightly longer timeout
                st.get_servers([str(ch["id"])])
                best = st.get_best_server()

                t0 = time.perf_counter()
                down = st.download(threads=THREADS) / 1e6
                up   = st.upload(threads=THREADS)   / 1e6
                duration = round(time.perf_counter() - t0, 2)
                lat = best.get("latency")

                res = {
                    "test_id": str(uuid.uuid4()),
                    "target_isp": target.capitalize(),
                    "speedtest_server": ch["name"],
                    "speedtest_sponsor": ch["sponsor"],
                    "speedtest_country": ch["country"],
                    "server_id": ch["id"],
                    "latency_ms": round(lat, 2) if lat else None,
                    "download_mbps": round(down, 2),
                    "upload_mbps": round(up, 2),
                    "duration_s": duration,
                    "threads_used": THREADS
                }

                print(f"✅ {target.upper()} ↓{res['download_mbps']} ↑{res['upload_mbps']} Mbps "
                      f"(lat {res['latency_ms']} ms, dur {res['duration_s']} s, thr {THREADS})\n")
                save_last_good(target, ch)
                return res

            except Exception as e:
                failure_count += 1
                print(f"⚠️ {target} error: {e}")
                time.sleep(5)

        # try next server
    print(f"❌ {target.upper()} failed after attempts ({failure_count} errors total)")

    # 🔁 Auto-healing trigger: clear cache and rediscover once
    if failure_count >= retries * 2:
        print(f"♻️ Re-discovering servers for {target.upper()} after repeated failures…")
        save_cached_servers({"etisalat": [], "du": []})
        discover_servers()
    return None

# ========= LOGGING =========
def day_paths():
    d = datetime.now().strftime("%Y-%m-%d")
    return (os.path.join(LOG_DIR, f"logs_{d}.csv"),
            os.path.join(LOG_DIR, f"logs_{d}.txt"))

def ensure_headers(csvp):
    if not os.path.exists(csvp) or os.path.getsize(csvp) == 0:
        with open(csvp, "w", newline="") as f:
            csv.writer(f).writerow([
                "ts_iso", "device", "hostname", "local_ip", "public_ip",
                "city", "region", "country", "lat", "lon", "isp",
                "test_id", "target_isp", "speedtest_server", "speedtest_sponsor",
                "speedtest_country", "server_id", "latency_ms",
                "download_mbps", "upload_mbps", "duration_s", "threads_used",
                "rtt_ms", "jitter_ms", "http_load_s"
            ])

def append_csv(csvp, row):
    ensure_headers(csvp)
    with open(csvp, "a", newline="") as f:
        csv.writer(f).writerow([row.get(k) for k in [
            "ts_iso", "device", "hostname", "local_ip", "public_ip",
            "city", "region", "country", "lat", "lon", "isp",
            "test_id", "target_isp", "speedtest_server", "speedtest_sponsor",
            "speedtest_country", "server_id", "latency_ms",
            "download_mbps", "upload_mbps", "duration_s", "threads_used",
            "rtt_ms", "jitter_ms", "http_load_s"
        ]])

def append_txt(txtp, msg):
    open(txtp, "a").write(msg + "\n")

# ========= SUPABASE PUSH =========
def supabase_push(row):
    if not (SUPABASE_URL and SUPABASE_ANON_KEY and SUPABASE_TABLE):
        print("❌ [Supabase] Missing credentials")
        return
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    try:
        r = requests.post(url, headers=headers, data=json.dumps(row), timeout=15)
        print(f"[Supabase] → {r.status_code}")
        if not r.ok:
            print(f"[Supabase] Error: {r.text}")
    except Exception as e:
        print(f"❌ Supabase push error: {e}")

# ========= MAIN LOOP =========
_stop = False
def _graceful_exit(sig, frm):
    global _stop
    _stop = True
signal.signal(signal.SIGINT, _graceful_exit)
signal.signal(signal.SIGTERM, _graceful_exit)

def main_loop():
    host = socket.gethostname()
    cycle = 0
    # Reset discovery cache every reboot for freshness
    save_cached_servers({"etisalat": [], "du": []})
    while not _stop:
        cycle += 1
        try:
            print(f"\n🌀 Cycle {cycle} started ({datetime.now().isoformat(timespec='seconds')})")
            csvp, txtp = day_paths()
            ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
            local_ip = get_local_ip()
            geo = get_ipinfo()
            rtt, jit = run_ping()
            http_s = measure_http_load()

            for isp in ["etisalat", "du"]:
                s = run_speedtest_dynamic(isp)
                if not s:
                    append_txt(txtp, f"[{ts}] {isp.upper()} test failed")
                    continue
                row = {
                    "ts_iso": ts, "device": DEVICE_ID, "hostname": host,
                    "local_ip": local_ip, "public_ip": geo["public_ip"],
                    "city": geo["city"], "region": geo["region"],
                    "country": geo["country"], "lat": geo["lat"], "lon": geo["lon"],
                    "isp": geo["isp"], **s,
                    "rtt_ms": rtt, "jitter_ms": jit, "http_load_s": http_s
                }
                append_csv(csvp, row)
                supabase_push(row)
                msg = f"[{ts}] ✅ {isp.upper()} ↓{s['download_mbps']} ↑{s['upload_mbps']} Mbps (dur {s['duration_s']} s)"
                print(msg)
                append_txt(txtp, msg)
                time.sleep(5)

        except Exception as e:
            print(f"❌ Loop error: {e}")

        finally:
            sleep_time = INTERVAL_SECONDS + random.randint(-30, 30)
            print(f"🕒 Sleeping {sleep_time}s …\n")
            for _ in range(sleep_time):
                if _stop:
                    break
                time.sleep(1)

if __name__ == "__main__":
    main_loop()



