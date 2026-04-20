import ccxt
import socket

orig_getaddrinfo = socket.getaddrinfo

def getaddrinfo_ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

socket.getaddrinfo = getaddrinfo_ipv4_only

proxy = 'socks5h://127.0.0.1:10808'

print("=== Test 1: binance (default) with SOCKS5 proxy ===")
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
    b = e.fetch_balance()
    u = b.get('USDT', {})
    print(f'OK! USDT free={u.get("free",0)}, used={u.get("used",0)}, total={u.get("total",0)}')
except Exception as ex:
    print(f'FAILED: {str(ex)[:200]}')

print("\n=== Test 2: binanceusdm with SOCKS5 proxy ===")
try:
    e2 = ccxt.binanceusdm({
        'apiKey': 'bwvtEMWL6jztGXbPLYS76ytXBuNeu9ziVFR5GRi9G7q1V6mLwwPMRO19ZVcGGJpS',
        'secret': 'erocH6kh8oQudLqVrlziGvnECccnu86mciGKHbzDvltAXBgvBj1uDmaNLyu1qp8u',
        'enableRateLimit': True,
        'options': {'adjustForTimeDifference': True},
        'proxies': {'http': proxy, 'https': proxy},
        'aiohttp_proxy': proxy,
    })
    e2.has['fetchCurrencies'] = False
    b2 = e2.fetch_balance()
    u2 = b2.get('USDT', {})
    print(f'OK! USDT free={u2.get("free",0)}, used={u2.get("used",0)}, total={u2.get("total",0)}')
except Exception as ex:
    print(f'FAILED: {str(ex)[:200]}')

socket.getaddrinfo = orig_getaddrinfo
