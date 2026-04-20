import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from crypto_trader.execution.exchange import create_exchange_from_config

async def check():
    exchange = create_exchange_from_config()
    symbol = 'BTC/USDT:USDT'
    results = []

    try:
        orders = await exchange.get_open_orders(symbol)
        results.append(f'Total open orders count: {len(orders)}')
        for o in orders:
            results.append(f'  id={o.order_id} type={o.order_type.value} side={o.side.value} amount={o.amount} price={o.price} metadata={o.metadata}')
    except Exception as e:
        results.append(f'Error fetching orders: {e}')

    try:
        positions = await exchange.get_positions()
        for p in positions:
            if p.amount and float(p.amount) > 0:
                results.append(f'Position: {p.symbol} side={p.side.value} amount={p.amount} entry={p.entry_price} pnl={p.unrealized_pnl}')
            else:
                results.append(f'No open position for {p.symbol}')
    except Exception as e:
        results.append(f'Error fetching positions: {e}')

    results.append('')
    results.append('=== Now cancelling all orders (regular + algo) ===')
    try:
        ok = await exchange.cancel_all_orders(symbol)
        results.append(f'cancel_all_orders result: {ok}')
    except Exception as e:
        results.append(f'Error cancelling orders: {e}')

    await asyncio.sleep(2)

    try:
        orders2 = await exchange.get_open_orders(symbol)
        results.append(f'After cancel - Total open orders count: {len(orders2)}')
        for o in orders2:
            results.append(f'  id={o.order_id} type={o.order_type.value} side={o.side.value} amount={o.amount} price={o.price} metadata={o.metadata}')
    except Exception as e:
        results.append(f'Error fetching orders after cancel: {e}')

    with open('check_result.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(results))

asyncio.run(check())
