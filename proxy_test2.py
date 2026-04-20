import requests
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROXY = {
    "http": "http://127.0.0.1:10809",
    "https": "http://127.0.0.1:10809"
}

results = []

def log(msg):
    print(msg)
    results.append(msg)

log("=" * 50)
log("Testing proxy + Binance API")
log("=" * 50)

try:
    log("\n[1/3] Testing proxy IP...")
    ip_resp = requests.get("https://api.ipify.org", proxies=PROXY, timeout=10)
    current_ip = ip_resp.text.strip()
    log(f"Current exit IP: {current_ip}")
except Exception as e:
    log(f"IP check failed: {e}")

try:
    log("\n[2/3] Testing Binance public API...")
    binance_resp = requests.get("https://api.binance.com/api/v3/ping", proxies=PROXY, timeout=10)
    log(f"Binance API status: {binance_resp.status_code}")
    if binance_resp.status_code == 200:
        log("Binance API OK!")
    else:
        log(f"Binance API FAILED: {binance_resp.status_code}")
        log(f"Response: {binance_resp.text[:200]}")
except Exception as e:
    log(f"Binance API error: {e}")

try:
    log("\n[3/3] Testing Binance Demo API...")
    demo_resp = requests.get("https://demo-api.binance.com/api/v3/ping", proxies=PROXY, timeout=10)
    log(f"Demo API status: {demo_resp.status_code}")
    if demo_resp.status_code == 200:
        log("Demo API OK!")
    else:
        log(f"Demo API FAILED: {demo_resp.status_code}")
except Exception as e:
    log(f"Demo API error: {e}")

try:
    log("\n[4] Testing Binance Futures API...")
    fapi_resp = requests.get("https://fapi.binance.com/fapi/v1/ping", proxies=PROXY, timeout=10)
    log(f"Futures API status: {fapi_resp.status_code}")
    if fapi_resp.status_code == 200:
        log("Futures API OK!")
    else:
        log(f"Futures API FAILED: {fapi_resp.status_code}")
        log(f"Response: {fapi_resp.text[:200]}")
except Exception as e:
    log(f"Futures API error: {e}")

log("\n" + "=" * 50)

with open("c:/Users/ll552/Desktop/8项修复/proxy_test_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))
