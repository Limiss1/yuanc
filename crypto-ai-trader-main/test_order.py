import ccxt
import time

API_KEY = 'byP9OnhnX9cPu5pxha6kiUoJadr5T2iMtYsTNjjyjcUraz67XXopCRPMrWIeV6OR'
API_SECRET = 'ACxfG5yCoVhrBcjb8vt9NjgC5AiBXoGeQonGEJGJLTvrzFq8E0kgKdDylUhPu4y6'
TESTNET_BASE = 'https://testnet.binancefuture.com'
SYMBOL = 'BTC/USDT:USDT'

result_file = open('test_order_result.txt', 'w', encoding='utf-8')

def log(msg):
    print(msg, flush=True)
    result_file.write(msg + '\n')
    result_file.flush()

log("--- Test: Real order on testnet with positionSide ---")
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
    exchange.has['fetchCurrencies'] = False

    log("1. load_markets...")
    exchange.load_markets()
    log(f"  Markets: {len(exchange.markets)}")

    log("\n2. fetch_balance...")
    balance = exchange.fetch_balance()
    usdt_free = balance.get('free', {}).get('USDT', 0)
    log(f"  USDT Free: {usdt_free}")

    log("\n3. set_leverage 10x...")
    result = exchange.set_leverage(10, SYMBOL)
    log(f"  Leverage: {result}")

    log("\n4. Try switching to ONE-WAY mode...")
    try:
        result = exchange.fapiPrivatePostPositionSideDual({
            'dualSidePosition': 'false'
        })
        log(f"  Result: {result}")
    except Exception as e:
        log(f"  Error (may already be one-way): {type(e).__name__}: {str(e)[:300]}")

    log("\n5. fetch_ticker...")
    ticker = exchange.fetch_ticker(SYMBOL)
    price = ticker['last']
    log(f"  BTC/USDT price: {price}")

    log("\n6. create_order SELL 0.001 BTC (short)...")
    try:
        order = exchange.create_order(
            symbol=SYMBOL,
            type='market',
            side='sell',
            amount=0.001
        )
        log(f"  Order ID: {order['id']}")
        log(f"  Status: {order['status']}")
        log(f"  Price: {order.get('average', order.get('price'))}")
        log(f"  Filled: {order.get('filled')}")
        log("  SUCCESS!")
    except Exception as e:
        log(f"  Error: {type(e).__name__}: {str(e)[:500]}")

    log("\n7. fetch_positions...")
    try:
        positions = exchange.fetch_positions([SYMBOL])
        for pos in positions:
            contracts = pos.get('contracts', 0)
            if contracts and contracts > 0:
                log(f"  {pos['symbol']}: side={pos['side']}, contracts={contracts}, entryPrice={pos['entryPrice']}, unrealizedPnl={pos.get('unrealizedPnl')}")
        log("  SUCCESS!")
    except Exception as e:
        log(f"  Error: {type(e).__name__}: {str(e)[:300]}")

    log("\n8. close position (buy 0.001)...")
    try:
        order = exchange.create_order(
            symbol=SYMBOL,
            type='market',
            side='buy',
            amount=0.001,
            params={'reduceOnly': True}
        )
        log(f"  Order ID: {order['id']}")
        log(f"  Status: {order['status']}")
        log("  SUCCESS!")
    except Exception as e:
        log(f"  Error: {type(e).__name__}: {str(e)[:500]}")

    log("\n9. fetch_balance after close...")
    balance = exchange.fetch_balance()
    usdt_free = balance.get('free', {}).get('USDT', 0)
    log(f"  USDT Free: {usdt_free}")

    log("\n=== ALL TESTS DONE! ===")

except Exception as e:
    log(f"Error: {type(e).__name__}: {str(e)[:500]}")

result_file.close()
