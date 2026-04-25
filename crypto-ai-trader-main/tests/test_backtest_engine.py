from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from crypto_trader.backtest import BacktestEngine, HistoricalReplayDataFeed
from crypto_trader.strategy.base import Signal, SignalType, Strategy


class AlternatingStrategy(Strategy):
    async def analyze(self, data, symbol):
        df = await data.get_ohlcv(symbol, limit=5, use_cache=False)
        price = float(df.iloc[-1]["close"])
        idx = len(df)
        signal_type = SignalType.BUY if idx % 2 == 0 else SignalType.SELL
        return Signal(
            signal_type=signal_type,
            symbol=symbol,
            confidence=0.9,
            price=price,
            timestamp=df.index[-1].to_pydatetime(),
        )


def _make_history(rows: int = 140) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=rows, freq="1min")
    base = pd.Series(range(rows), index=index, dtype=float)
    return pd.DataFrame(
        {
            "open": 100 + base,
            "high": 101 + base,
            "low": 99 + base,
            "close": 100 + base,
            "volume": 1000.0,
        },
        index=index,
    )


@pytest.mark.asyncio
async def test_historical_replay_data_feed_reveals_only_visible_window():
    history = _make_history(10)
    feed = HistoricalReplayDataFeed({"BTC/USDT:USDT": history})
    feed.set_cursor("BTC/USDT:USDT", 4)

    visible = await feed.fetch_ohlcv("BTC/USDT:USDT", limit=100)

    assert len(visible) == 5
    assert visible.index[-1] == history.index[4]


@pytest.mark.asyncio
async def test_backtest_engine_runs_with_existing_trading_stack():
    history = _make_history(140)
    config = SimpleNamespace(
        symbols=["BTC/USDT:USDT"],
        exchange=SimpleNamespace(leverage=5),
        strategy=SimpleNamespace(lookback_period=20),
        risk=SimpleNamespace(
            max_drawdown=0.15,
            daily_loss_limit=0.05,
            max_open_positions=3,
            stop_loss_pct=0.0015,
            take_profit_pct=0.003,
        ),
    )

    engine = BacktestEngine(
        config=config,
        strategy=AlternatingStrategy(),
        historical_data={"BTC/USDT:USDT": history},
        initial_balance=1000.0,
    )

    result = await engine.run()

    assert result.candles == 140
    assert result.final_equity > 0
    assert result.trade_count >= 0
    assert result.signal_count > 0


@pytest.mark.asyncio
async def test_backtest_engine_does_not_restore_persisted_runtime_state(monkeypatch):
    history = _make_history(140)
    config = SimpleNamespace(
        symbols=["BTC/USDT:USDT"],
        exchange=SimpleNamespace(leverage=5),
        strategy=SimpleNamespace(lookback_period=20),
        risk=SimpleNamespace(
            max_drawdown=0.15,
            daily_loss_limit=0.05,
            max_open_positions=3,
            stop_loss_pct=0.0015,
            take_profit_pct=0.003,
        ),
    )
    state_file = Path(__file__).resolve().parent / "_tmp_backtest_state.json"
    state_file.write_text('{"confidence_threshold": 0.95, "trade_count": 999}', encoding="utf-8")

    import crypto_trader.execution.trading_engine as trading_engine_module

    monkeypatch.setattr(trading_engine_module, "STATE_FILE", state_file)

    try:
        engine = BacktestEngine(
            config=config,
            strategy=AlternatingStrategy(),
            historical_data={"BTC/USDT:USDT": history},
            initial_balance=1000.0,
        )

        assert engine.engine.confidence_threshold == 0.6
        assert engine.engine.trade_count == 0
    finally:
        state_file.unlink(missing_ok=True)
