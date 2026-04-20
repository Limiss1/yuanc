import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from crypto_trader.execution.exchange import create_exchange_from_config
from crypto_trader.execution.exchange import OrderSide, OrderType

async def cleanup():
    exchange = create_exchange_from_config()
    symbol = 'BTC/USDT:USDT'
    results = []

    try:
        results.append("=== Step 1: Cancel all regular orders ===")
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, lambda: exchange.exchange.cancel_all_orders(symbol))
            results.append("Cancelled all regular orders")
        except Exception as e:
            results.append(f"Regular cancel error: {e}")
    except Exception as e:
        results.append(f"Step 1 error: {e}")

    await asyncio.sleep(2)

    try:
        results.append("\n=== Step 1b: Cancel all algo orders ===")
        loop = asyncio.get_event_loop()
        binance_symbol = symbol.replace('/', '').replace(':USDT', '')
        try:
            algo_result = await loop.run_in_executor(
                None,
                lambda: exchange.exchange.fapiPrivateDeleteAlgoOpenOrders({'symbol': binance_symbol})
            )
            results.append(f"Algo cancel result: {algo_result}")
        except Exception as e:
            results.append(f"Algo cancel error: {e}")
    except Exception as e:
        results.append(f"Step 1b error: {e}")

    await asyncio.sleep(2)

    try:
        results.append("\n=== Step 2: Close all positions ===")
        positions = await exchange.get_positions()
        for pos in positions:
            if pos.symbol == symbol and pos.amount and float(pos.amount) > 0:
                close_side = OrderSide.SELL if pos.side.value == 'buy' else OrderSide.BUY
                try:
                    close_order = await exchange.create_order(
                        symbol=symbol,
                        order_type=OrderType.MARKET,
                        side=close_side,
                        amount=pos.amount,
                        metadata={'reduce_only': True}
                    )
                    results.append(f"Closed position: {pos.side.value} {pos.amount}, order_id={close_order.order_id}")
                except Exception as e:
                    results.append(f"Failed to close position: {e}")
    except Exception as e:
        results.append(f"Step 2 error: {e}")

    await asyncio.sleep(2)

    try:
        results.append("\n=== Step 3: Final cancel all ===")
        ok = await exchange.cancel_all_orders(symbol)
        results.append(f"Final cancel_all_orders: {ok}")
    except Exception as e:
        results.append(f"Step 3 error: {e}")

    await asyncio.sleep(2)

    try:
        results.append("\n=== Step 4: Verify ===")
        orders = await exchange.get_open_orders(symbol)
        results.append(f"Open orders: {len(orders)}")
        for o in orders:
            results.append(f"  {o.order_id} {o.order_type.value} {o.side.value} {o.amount}")

        positions = await exchange.get_positions()
        for p in positions:
            if p.symbol == symbol:
                if p.amount and float(p.amount) > 0:
                    results.append(f"Position: {p.side.value} {p.amount}")
                else:
                    results.append(f"No position")
    except Exception as e:
        results.append(f"Step 4 error: {e}")

    with open('cleanup_result.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(results))

asyncio.run(cleanup())
