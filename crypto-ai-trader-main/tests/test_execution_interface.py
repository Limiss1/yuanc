from decimal import Decimal

import pytest

from crypto_trader.execution.exchange import OrderSide, OrderType
from crypto_trader.execution.paper_exchange import PaperExchange


@pytest.mark.asyncio
async def test_create_market_order_alias_works_with_string_side():
    exchange = PaperExchange(
        initial_balance={"USDT": 1000.0},
        default_leverage=10,
        use_api_balance=False,
    )
    await exchange.update_market_prices({"BTC/USDT:USDT": Decimal("75000")})

    order = await exchange.create_market_order(
        symbol="BTC/USDT:USDT",
        side="buy",
        amount=Decimal("0.001"),
    )

    assert order.order_type == OrderType.MARKET
    assert order.side == OrderSide.BUY
    assert order.price == Decimal("75000")

    positions = await exchange.fetch_positions("BTC/USDT:USDT")
    assert len(positions) == 1
    assert positions[0].side == OrderSide.BUY
    assert positions[0].amount == Decimal("0.001")


@pytest.mark.asyncio
async def test_create_market_order_alias_maps_reduce_only_params():
    exchange = PaperExchange(
        initial_balance={"USDT": 1000.0},
        default_leverage=10,
        use_api_balance=False,
    )
    await exchange.update_market_prices({"BTC/USDT:USDT": Decimal("75000")})

    await exchange.create_market_order(
        symbol="BTC/USDT:USDT",
        side="buy",
        amount=Decimal("0.001"),
    )

    close_order = await exchange.create_market_order(
        symbol="BTC/USDT:USDT",
        side="sell",
        amount=Decimal("0.001"),
        params={"reduceOnly": True},
    )

    assert close_order.metadata["paper_trade"] is True
    positions = await exchange.fetch_positions("BTC/USDT:USDT")
    assert positions == []
