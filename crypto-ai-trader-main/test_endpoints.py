import requests

endpoints = [
    ('fapi1', 'https://fapi1.binance.com/fapi/v1/ping'),
    ('fapi2', 'https://fapi2.binance.com/fapi/v1/ping'),
    ('fapi3', 'https://fapi3.binance.com/fapi/v1/ping'),
    ('fapi4', 'https://fapi4.binance.com/fapi/v1/ping'),
    ('api1', 'https://api1.binance.com/api/v3/ping'),
    ('api2', 'https://api2.binance.com/api/v3/ping'),
    ('api3', 'https://api3.binance.com/api/v3/ping'),
    ('api4', 'https://api4.binance.com/api/v3/ping'),
]

print("=== Direct (no proxy) ===")
for name, url in endpoints:
    try:
        r = requests.get(url, timeout=8)
        status = 'OK' if r.status_code == 200 else f'FAIL({r.status_code})'
        print(f'  {status} - {name}: {url}')
    except Exception as e:
        print(f'  ERROR - {name}: {str(e)[:60]}')

print("\n=== SOCKS5 proxy ===")
p = {'http': 'socks5h://127.0.0.1:10808', 'https': 'socks5h://127.0.0.1:10808'}
for name, url in endpoints:
    try:
        r = requests.get(url, proxies=p, timeout=8)
        status = 'OK' if r.status_code == 200 else f'FAIL({r.status_code})'
        print(f'  {status} - {name}: {url}')
    except Exception as e:
        print(f'  ERROR - {name}: {str(e)[:60]}')
