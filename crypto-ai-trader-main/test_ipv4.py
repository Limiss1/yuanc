import requests
import socket
from urllib3.util.connection import ALLOWED_ADDRESSES

orig_getaddrinfo = socket.getaddrinfo

def getaddrinfo_ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

socket.getaddrinfo = getaddrinfo_ipv4_only

try:
    r = requests.get('https://api64.ipify.org', timeout=15)
    print('IPv4 IP:', r.text)
except Exception as e:
    print(f'IP check failed: {e}')

try:
    r = requests.get('https://fapi.binance.com/fapi/v1/ping', timeout=15)
    print('Binance fapi:', r.status_code, r.text[:100])
except Exception as e:
    print(f'Binance fapi failed: {e}')

try:
    r = requests.get('https://api.binance.com/api/v3/ping', timeout=15)
    print('Binance spot:', r.status_code, r.text[:100])
except Exception as e:
    print(f'Binance spot failed: {e}')

socket.getaddrinfo = orig_getaddrinfo
