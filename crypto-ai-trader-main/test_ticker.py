import asyncio
import ccxt

async def test():
    exchange = ccxt.binanceusdm({
        'apiKey': 'byP9OnhnX9cPu5pxha6kiUoJadr5T2iMtYsTNjjyjcUraz67XXopCRPMrWIeV6OR',
        'secret': 'ACxfG5yCoVhrBcjb8vt9NjgC5AiBXoGeQonGEJGJLTvrzFq8E0kgKdDylUhPu4y6',
        'enableRateLimit': True,
        'timeout': 15000,
        'proxies': {
            'http': 'http://127.0.0.1:10809',
            'https': 'http://127.0.0.1:10809',
        },
        'aiohttp_proxy': 'http://127.0.0.1:10809',
    })

    TESTNET_BASE = 'https://testnet.binancefuture.com'
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

    loop = asyncio.get_event_loop()
    ticker = await loop.run_in_executor(None, lambda: exchange.fetch_ticker('BTC/USDT:USDT'))
    print(f"BTC/USDT:USDT price: {ticker['last']}")
    print(f"Symbol: {ticker['symbol']}")

asyncio.run(test())
