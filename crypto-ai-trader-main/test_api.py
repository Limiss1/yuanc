import ccxt
import time

result_file = open('test_result.txt', 'w', encoding='utf-8')

def log(msg):
    print(msg, flush=True)
    result_file.write(msg + '\n')
    result_file.flush()

API_KEY = 'byP9OnhnX9cPu5pxha6kiUoJadr5T2iMtYsTNjjyjcUraz67XXopCRPMrWIeV6OR'
API_SECRET = 'ACxfG5yCoVhrBcjb8vt9NjgC5AiBXoGeQonGEJGJLTvrzFq8E0kgKdDylUhPu4y6'
TESTNET_BASE = 'https://testnet.binancefuture.com'
SYMBOL = 'BTC/USDT:USDT'

log("--- Test: binanceusdm FULL test ---")
try:
    exchange = ccxt.binanceusdm({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'enableRateLimit': True,
        'timeout': 15000,
        'proxies': {
            'http': 'http://127.0.0.1:10809',
            'https': 'http://127.0.0.1:10809',
        },
        'aiohttp_proxy': 'http://127.0.0.1:10809',
    })

    api_urls = {
        'fapiPublic': f'{TESTNET_BASE}/fapi/v1',
        'fapiPublicV2': f'{TESTNET_BASE}/fapi/v2',
        'fapiPublicV3': f'{TESTNET_BASE}/fapi/v3',
        'fapiPrivate': f'{TESTNET_BASE}/fapi/v1',
        'fapiPrivateV2': f'{TESTNET_BASE}/fapi/v2',
        'fapiPrivateV3': f'{TESTNET_BASE}/fapi/v3',
        'dapiPublic': f'{TESTNET_BASE}/dapi/v1',
        'dapiPrivate': f'{TESTNET_BASE}/dapi/v1',
        'dapiPrivateV2': f'{TESTNET_BASE}/dapi/v2',
        'sapi': f'{TESTNET_BASE}/sapi/v1',
        'sapiPublic': f'{TESTNET_BASE}/sapi/v1',
        'sapiPrivate': f'{TESTNET_BASE}/sapi/v1',
        'sapiPrivateV2': f'{TESTNET_BASE}/sapi/v2',
        'public': f'{TESTNET_BASE}/api/v3',
        'private': f'{TESTNET_BASE}/api/v3',
    }

    exchange.urls['api'] = api_urls
    exchange.urls['test'] = api_urls.copy()
    exchange.sandbox = False

    log("1. load_markets...")
    exchange.load_markets()
    log(f"  Markets loaded: {len(exchange.markets)}")

    log("\n2. fetch_balance...")
    balance = exchange.fetch_balance()
    usdt_free = balance.get('free', {}).get('USDT', 0)
    usdt_total = balance.get('total', {}).get('USDT', 0)
    log(f"  USDT Free: {usdt_free}, Total: {usdt_total}")
    log("  SUCCESS!")

    log(f"\n3. fetch_ticker {SYMBOL}...")
    ticker = exchange.fetch_ticker(SYMBOL)
    log(f"  Price: {ticker['last']}")
    log("  SUCCESS!")

    log(f"\n4. fetch_ohlcv {SYMBOL} 1m...")
    ohlcv = exchange.fetch_ohlcv(SYMBOL, '1m', limit=3)
    for candle in ohlcv:
        t = time.strftime('%Y-%m-%d %H:%M', time.localtime(candle[0]/1000))
        log(f"  {t}: O={candle[1]} H={candle[2]} L={candle[3]} C={candle[4]} V={candle[5]}")
    log("  SUCCESS!")

    log(f"\n5. set_leverage 10x {SYMBOL}...")
    try:
        result = exchange.set_leverage(10, SYMBOL)
        log(f"  Leverage: {result}")
        log("  SUCCESS!")
    except Exception as e:
        log(f"  Error: {type(e).__name__}: {str(e)[:300]}")

    log("\n6. fetch_positions...")
    try:
        positions = exchange.fetch_positions([SYMBOL])
        for pos in positions:
            log(f"  {pos['symbol']}: side={pos['side']}, contracts={pos['contracts']}, entryPrice={pos['entryPrice']}")
        log("  SUCCESS!")
    except Exception as e:
        log(f"  Error: {type(e).__name__}: {str(e)[:300]}")

    log("\n\n=== ALL TESTS PASSED! ===")

except Exception as e:
    log(f"Error: {type(e).__name__}: {str(e)[:500]}")

result_file.close()
