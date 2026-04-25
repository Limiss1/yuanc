"""
Backtest engine built on top of the live trading stack.
Replays historical candles through the existing strategy, risk, and execution layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd

from ..data.market_data import DataFeed, MarketData
from ..execution.paper_exchange import PaperExchange
from ..execution.trading_engine import TradingEngine
from ..infra.config import TradingConfig
from ..infra.logger import LogMixin
from ..risk.risk_manager import RiskManager
from ..strategy.base import Strategy


class HistoricalReplayDataFeed(DataFeed):
    """Replay historical candles as if they were arriving in real time."""

    def __init__(self, history_by_symbol: Dict[str, pd.DataFrame]):
        super().__init__()
        self.history_by_symbol = {
            symbol: df.sort_index().copy()
            for symbol, df in history_by_symbol.items()
        }
        self.current_index_by_symbol: Dict[str, int] = {
            symbol: 0 for symbol in self.history_by_symbol
        }

    def set_cursor(self, symbol: str, index: int) -> None:
        if symbol not in self.history_by_symbol:
            raise KeyError(f"Unknown symbol for replay: {symbol}")
        max_index = len(self.history_by_symbol[symbol]) - 1
        self.current_index_by_symbol[symbol] = max(0, min(index, max_index))

    def _slice_history(
        self,
        symbol: str,
        limit: int,
        since: Optional[int] = None,
    ) -> pd.DataFrame:
        if symbol not in self.history_by_symbol:
            raise KeyError(f"Unknown symbol for replay: {symbol}")

        full_df = self.history_by_symbol[symbol]
        current_index = self.current_index_by_symbol[symbol]
        visible = full_df.iloc[: current_index + 1]

        if since is not None:
            since_ts = pd.to_datetime(since, unit="ms")
            visible = visible[visible.index >= since_ts]

        if limit > 0:
            visible = visible.tail(limit)

        return visible.copy()

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
        limit: int = 100,
        since: Optional[int] = None,
    ) -> pd.DataFrame:
        return self._slice_history(symbol, limit=limit, since=since)

    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        latest = self._slice_history(symbol, limit=1)
        if latest.empty:
            return {
                "symbol": symbol,
                "last": 0.0,
                "bid": 0.0,
                "ask": 0.0,
                "timestamp": int(datetime.now().timestamp() * 1000),
            }

        row = latest.iloc[-1]
        close_price = float(row["close"])
        return {
            "symbol": symbol,
            "last": close_price,
            "bid": close_price,
            "ask": close_price,
            "timestamp": int(latest.index[-1].timestamp() * 1000),
        }

    async def fetch_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        ticker = await self.fetch_ticker(symbol)
        price = ticker["last"]
        return {
            "bids": [[price, 1.0]],
            "asks": [[price, 1.0]],
            "timestamp": ticker["timestamp"],
        }


@dataclass
class BacktestResult:
    symbol: str
    candles: int
    warmup_candles: int
    initial_balance: float
    final_equity: float
    total_return_pct: float
    total_pnl: float
    max_drawdown_pct: float
    trade_count: int
    signal_count: int
    win_rate: float
    win_count: int
    loss_count: int
    total_closed: int
    position_count: int
    buy_and_hold_return_pct: float
    start_time: str
    end_time: str
    portfolio: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "candles": self.candles,
            "warmup_candles": self.warmup_candles,
            "initial_balance": self.initial_balance,
            "final_equity": self.final_equity,
            "total_return_pct": self.total_return_pct,
            "total_pnl": self.total_pnl,
            "max_drawdown_pct": self.max_drawdown_pct,
            "trade_count": self.trade_count,
            "signal_count": self.signal_count,
            "win_rate": self.win_rate,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "total_closed": self.total_closed,
            "position_count": self.position_count,
            "buy_and_hold_return_pct": self.buy_and_hold_return_pct,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "portfolio": self.portfolio,
        }


class BacktestEngine(LogMixin):
    """Run a historical replay backtest using the existing trading engine."""

    def __init__(
        self,
        config: TradingConfig,
        strategy: Strategy,
        historical_data: Dict[str, pd.DataFrame],
        initial_balance: float = 10000.0,
        risk_manager: Optional[RiskManager] = None,
    ):
        super().__init__()
        self.config = config
        self.strategy = strategy
        self.historical_data = historical_data
        self.initial_balance = initial_balance
        self.replay_feed = HistoricalReplayDataFeed(historical_data)
        self.market_data = MarketData(self.replay_feed)
        self.market_data.cache_ttl = timedelta(seconds=0)
        self.exchange = PaperExchange(
            initial_balance={"USDT": initial_balance},
            default_leverage=config.exchange.leverage,
            use_api_balance=False,
        )
        self.risk_manager = risk_manager or RiskManager(config.risk)
        self.engine = TradingEngine(
            config=config,
            strategy=strategy,
            exchange=self.exchange,
            market_data=self.market_data,
            risk_manager=self.risk_manager,
            persist_state=False,
        )
        self.equity_curve: List[float] = []

    @staticmethod
    def _validate_history(history: pd.DataFrame, symbol: str) -> pd.DataFrame:
        required = {"open", "high", "low", "close", "volume"}
        missing = required - set(history.columns)
        if missing:
            raise ValueError(f"Missing OHLCV columns for {symbol}: {sorted(missing)}")
        if history.empty:
            raise ValueError(f"No historical data available for {symbol}")
        return history.sort_index().copy()

    @staticmethod
    def _calculate_max_drawdown(equity_curve: List[float]) -> float:
        if not equity_curve:
            return 0.0

        peak = equity_curve[0]
        max_drawdown = 0.0
        for equity in equity_curve:
            peak = max(peak, equity)
            if peak > 0:
                drawdown = (peak - equity) / peak
                max_drawdown = max(max_drawdown, drawdown)
        return max_drawdown * 100

    async def run(self) -> BacktestResult:
        symbol = self.config.symbols[0]
        history = self._validate_history(self.historical_data[symbol], symbol)
        total_candles = len(history)

        if total_candles < 120:
            raise ValueError(
                f"Backtest requires at least 120 candles for {symbol}, got {total_candles}"
            )

        warmup = min(max(100, min(300, self.config.strategy.lookback_period)), total_candles - 1)
        self.logger.info(
            f"Backtest starting for {symbol}: candles={total_candles}, warmup={warmup}, "
            f"initial_balance={self.initial_balance:.2f}"
        )

        await self.engine._initialize_balance()

        for index in range(warmup, total_candles):
            self.replay_feed.set_cursor(symbol, index)
            self.market_data.clear_cache()
            await self.engine._trading_cycle()
            equity = self.exchange.get_portfolio_summary()["equity"]
            self.equity_curve.append(float(equity))

        final_price = Decimal(str(history.iloc[-1]["close"]))
        await self.exchange.update_market_prices({symbol: final_price})
        positions = await self.exchange.get_positions(symbol)
        for position in positions:
            close_side = "sell" if position.side.value == "buy" else "buy"
            await self.exchange.create_market_order(
                symbol=symbol,
                side=close_side,
                amount=position.amount,
                price=final_price,
                params={"reduceOnly": True},
            )
            self.engine.trade_count += 1

        portfolio = self.exchange.get_portfolio_summary()
        final_equity = float(portfolio["equity"])
        total_pnl = final_equity - float(self.initial_balance)
        total_return_pct = (
            (total_pnl / float(self.initial_balance)) * 100
            if self.initial_balance
            else 0.0
        )

        start_price = float(history.iloc[warmup]["close"])
        end_price = float(history.iloc[-1]["close"])
        buy_and_hold_return_pct = (
            ((end_price - start_price) / start_price) * 100 if start_price else 0.0
        )

        result = BacktestResult(
            symbol=symbol,
            candles=total_candles,
            warmup_candles=warmup,
            initial_balance=float(self.initial_balance),
            final_equity=final_equity,
            total_return_pct=total_return_pct,
            total_pnl=total_pnl,
            max_drawdown_pct=self._calculate_max_drawdown(self.equity_curve),
            trade_count=self.engine.trade_count,
            signal_count=self.engine.signal_count,
            win_rate=self.engine.win_rate,
            win_count=self.engine._win_count,
            loss_count=self.engine._loss_count,
            total_closed=self.engine._total_closed,
            position_count=int(portfolio["position_count"]),
            buy_and_hold_return_pct=buy_and_hold_return_pct,
            start_time=history.index[warmup].isoformat(),
            end_time=history.index[-1].isoformat(),
            portfolio=portfolio,
        )

        self.logger.info(
            f"Backtest complete for {symbol}: equity={result.final_equity:.2f}, "
            f"return={result.total_return_pct:+.2f}%, trades={result.trade_count}"
        )
        return result
