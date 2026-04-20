import ccxt
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

results = []

def log(msg):
    print(msg)
    results.append(msg)

proxy = 'http://127.0.0.1:10809'

log("=== Testing CCXT Binance Live API ===")

try:
    e = ccxt.binance({
        'apiKey': 'bwvtEMWL6jztGXbPLYS76ytXBuNeu9ziVFR5GRi9G7q1V6mLwwPMRO19ZVcGGJpS',
        'secret': 'erocH6kh8oQudLqVrlziGvnECccnu86mciGKHbzDvltAXBgvBj1uDmaNLyu1qp8u',
        'enableRateLimit': True,
        'options': {'defaultType': 'future', 'adjustForTimeDifference': True},
        'proxies': {'http': proxy, 'https': proxy},
        'aiohttp_proxy': proxy,
    })
    e.has['fetchCurrencies'] = False
    
    log("Fetching balance...")
    b = e.fetch_balance()
    u = b.get('USDT', {})
    free = u.get('free', 0)
    used = u.get('used', 0)
    total = u.get('total', 0)
    log(f"OK! USDT free={free}, used={used}, total={total}")
    
    log("Fetching positions...")
    positions = e.fetch_positions()
    open_pos = [p for p in positions if float(p.get('contracts', 0)) > 0]
    log(f"Open positions: {len(open_pos)}")
    for p in open_pos:
        log(f"  {p['symbol']}: {p['side']} {p['contracts']} @ {p['entryPrice']}")
    
except Exception as ex:
    log(f"FAILED: {str(ex)[:500]}")

with open("c:/Users/ll552/Desktop/8项修复/ccxt_test_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))
