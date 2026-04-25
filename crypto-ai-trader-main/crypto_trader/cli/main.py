"""
Command-line interface for Crypto Trader.
"""

import asyncio
import csv
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from crypto_trader.infra.config import load_config, get_config, TradingMode
from crypto_trader.infra.logger import setup_logger
from crypto_trader.data.market_data import create_data_feed_from_config, MarketData
from crypto_trader.backtest import BacktestEngine
from crypto_trader.execution.exchange import create_exchange_from_config
from crypto_trader.execution.paper_exchange import PaperExchange
from crypto_trader.execution.trading_engine import TradingEngine
from crypto_trader.strategy.ai_strategy import AIStrategy
from crypto_trader.risk.risk_manager import RiskManager


REPORTS_DIR = Path("reports")
BACKTEST_REPORTS_DIR = REPORTS_DIR / "backtests"
TRAINING_REPORTS_DIR = REPORTS_DIR / "training"


def _ensure_reports_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_symbol(symbol: str) -> str:
    return symbol.replace("/", "-").replace(":", "-")


def _period_to_minutes(period: str) -> int:
    period = period.strip().lower()
    if not period:
        raise ValueError("Training period cannot be empty")

    unit = period[-1]
    value_str = period[:-1]
    if not value_str.isdigit():
        raise ValueError(f"Unsupported training period: {period}")

    value = int(value_str)
    multipliers = {
        "m": 1,
        "h": 60,
        "d": 24 * 60,
    }
    if unit not in multipliers:
        raise ValueError(f"Unsupported training period unit: {period}")
    return value * multipliers[unit]


def _write_csv_report(path: Path, rows: list[dict]) -> Path:
    if not rows:
        path.write_text("", encoding="utf-8")
        return path

    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, config: Optional[str], verbose: bool):
    """Crypto Trader - High-frequency cryptocurrency trading system."""
    config_path = Path(config) if config else None
    ctx.obj = {
        'config': load_config(config_path),
        'verbose': verbose
    }

    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logger(level=log_level)

    logger = logging.getLogger(__name__)
    logger.info(f"Crypto Trader CLI initialized with config: {config_path}")


@cli.command()
@click.option('--symbol', '-s', multiple=True, help='Trading symbols (e.g., BTC/USDT)')
@click.option('--strategy', '-t', default='ai', help='Trading strategy (ai, dummy)')
@click.option('--mode', '-m', type=click.Choice(['backtest', 'paper', 'live']),
              default='paper', help='Trading mode')
@click.option('--balance', '-b', type=float, default=10000.0, help='Initial balance for paper trading (USDT)')
@click.pass_context
def trade(ctx, symbol: tuple, strategy: str, mode: str, balance: float):
    """Start trading with specified strategy."""
    config = ctx.obj['config']

    if symbol:
        config.symbols = list(symbol)

    mode_map = {
        'backtest': TradingMode.BACKTEST,
        'paper': TradingMode.PAPER_TRADING,
        'live': TradingMode.LIVE_TRADING
    }
    config.mode = mode_map[mode]

    logger = logging.getLogger(__name__)
    logger.info(f"Starting trading: symbols={config.symbols}, strategy={strategy}, mode={mode}")

    asyncio.run(_run_trading(config, strategy, balance))


@cli.command()
@click.option('--symbol', '-s', required=True, help='Trading symbol (e.g., BTC/USDT)')
@click.option('--days', '-d', type=int, default=30, help='Days of historical data')
@click.option('--strategy', '-t', default='ai', help='Trading strategy')
@click.pass_context
def backtest(ctx, symbol: str, days: int, strategy: str):
    """Run backtest with historical data."""
    config = ctx.obj['config']
    config.symbols = [symbol]
    config.mode = TradingMode.BACKTEST
    config.data.historical_days = days

    logger = logging.getLogger(__name__)
    logger.info(f"Starting backtest: symbol={symbol}, days={days}, strategy={strategy}")

    asyncio.run(_run_backtest(config, strategy))


@cli.command()
@click.option('--symbol', '-s', required=True, help='Trading symbol (e.g., BTC/USDT)')
@click.option('--period', '-p', default='90d', help='Training period (e.g., 30d, 90d)')
@click.pass_context
def train(ctx, symbol: str, period: str):
    """Train AI model with historical data."""
    config = ctx.obj['config']

    logger = logging.getLogger(__name__)
    logger.info(f"Training AI model: symbol={symbol}, period={period}")

    asyncio.run(_run_training(config, symbol, period))


@cli.command()
@click.option('--symbol', '-s', required=True, help='Trading symbol (e.g., BTC/USDT)')
@click.option('--period', '-p', default='30d', help='Training period (e.g., 30d, 90d)')
@click.option('--days', '-d', type=int, default=7, help='Backtest lookback days')
@click.option('--strategy', '-t', default='ai', help='Backtest strategy (ai, dummy)')
@click.pass_context
def research(ctx, symbol: str, period: str, days: int, strategy: str):
    """Run training and backtest as one research workflow."""
    config = ctx.obj['config']
    config.symbols = [symbol]
    config.data.historical_days = days
    config.mode = TradingMode.BACKTEST

    logger = logging.getLogger(__name__)
    logger.info(
        f"Running research workflow: symbol={symbol}, period={period}, days={days}, strategy={strategy}"
    )

    asyncio.run(_run_research(config, symbol, period, days, strategy))


@cli.command()
@click.pass_context
def status(ctx):
    """Show system status and configuration."""
    config = ctx.obj['config']

    click.echo("=== Crypto Trader Status ===")
    click.echo(f"Mode: {config.mode.value}")
    click.echo(f"Symbols: {', '.join(config.symbols)}")
    click.echo(f"Base Currency: {config.base_currency}")
    click.echo("")

    click.echo("=== Exchange Configuration ===")
    click.echo(f"Exchange: {config.exchange.name.value}")
    click.echo(f"Testnet: {config.exchange.testnet}")
    click.echo(f"API Key: {'Set' if config.exchange.api_key else 'Not set'}")
    click.echo("")

    click.echo("=== Strategy Configuration ===")
    click.echo(f"Strategy: {config.strategy.name}")
    click.echo(f"Confidence Threshold: {config.strategy.confidence_threshold:.0%}")
    click.echo(f"Max Position Size: {config.strategy.max_position_size:.0%}")
    click.echo("")

    click.echo("=== Risk Configuration ===")
    click.echo(f"Max Drawdown: {config.risk.max_drawdown:.0%}")
    click.echo(f"Daily Loss Limit: {config.risk.daily_loss_limit:.0%}")
    click.echo(f"Max Open Positions: {config.risk.max_open_positions}")
    click.echo("")


@cli.command()
@click.option('--all', '-a', is_flag=True, help='Run all tests')
@click.option('--unit', '-u', is_flag=True, help='Run unit tests only')
@click.option('--integration', '-i', is_flag=True, help='Run integration tests only')
@click.pass_context
def test(ctx, all: bool, unit: bool, integration: bool):
    """Run tests."""
    import pytest

    args = []

    if all or (not unit and not integration):
        args = ['tests/']
    elif unit:
        args = ['tests/test_config.py', 'tests/test_strategy.py']
    elif integration:
        args = ['tests/test_data.py']

    if ctx.obj['verbose']:
        args.append('-v')

    sys.exit(pytest.main(args))


async def _run_trading(config, strategy_name: str, initial_balance: float = 10000.0):
    """Run trading with specified strategy."""
    logger = logging.getLogger(__name__)

    try:
        data_feed = create_data_feed_from_config()
        market_data = MarketData(data_feed)

        if config.mode == TradingMode.PAPER_TRADING:
            exchange = PaperExchange(
                initial_balance={"USDT": initial_balance},
                default_leverage=config.exchange.leverage
            )
            logger.info(f"Paper trading (USDT Futures): balance={initial_balance} USDT, leverage={config.exchange.leverage}x")
        elif config.mode == TradingMode.LIVE_TRADING:
            exchange = create_exchange_from_config()
            logger.info("LIVE trading mode - using real exchange")
        else:
            exchange = PaperExchange(initial_balance={"USDT": initial_balance})
            logger.info("Backtest mode - using paper exchange")

        if strategy_name == 'ai':
            strategy = AIStrategy()
        else:
            from crypto_trader.strategy.base import DummyStrategy
            strategy = DummyStrategy()

        risk_manager = RiskManager()

        engine = TradingEngine(
            config=config,
            strategy=strategy,
            exchange=exchange,
            market_data=market_data,
            risk_manager=risk_manager
        )

        click.echo(f"\n{'='*50}")
        click.echo(f"  Trading Engine Started (USDT Futures)")
        click.echo(f"  Mode: {'PAPER' if config.mode == TradingMode.PAPER_TRADING else 'LIVE'}")
        click.echo(f"  Strategy: {strategy.__class__.__name__}")
        click.echo(f"  Symbols: {', '.join(config.symbols)}")
        click.echo(f"  Leverage: {config.exchange.leverage}x")
        if config.mode == TradingMode.PAPER_TRADING:
            click.echo(f"  Initial Balance: {initial_balance} USDT")
        click.echo(f"{'='*50}\n")

        loop = asyncio.get_running_loop()
        trading_task = asyncio.create_task(engine.run())

        try:
            while True:
                await asyncio.sleep(15)
                if trading_task.done():
                    exc = trading_task.exception()
                    if exc:
                        logger.error(f"Trading engine crashed: {exc}", exc_info=exc)
                    break
                await engine.refresh_prices()
                status = engine.get_status()
                if 'portfolio' in status:
                    p = status['portfolio']
                    if config.mode == TradingMode.PAPER_TRADING:
                        click.echo(
                            f"[{datetime.now().strftime('%H:%M:%S')}] "
                            f"Trades: {status['trade_count']} | "
                            f"Equity: {p.get('equity', p.get('total_value', 0)):.2f} | "
                            f"PnL: {p.get('total_pnl', 0):+.2f} ({p.get('total_pnl_pct', 0):+.2f}%) | "
                            f"Positions: {p.get('position_count', 0)}"
                        )
                    else:
                        click.echo(
                            f"[{datetime.now().strftime('%H:%M:%S')}] "
                            f"Trades: {status['trade_count']} | "
                            f"Equity: {p.get('equity', 0):.2f} | "
                            f"Positions: {p.get('position_count', 0)}"
                        )
        except KeyboardInterrupt:
            click.echo("\nStopping trading engine...")
            engine.stop()
            await trading_task

    except KeyboardInterrupt:
        logger.info("Trading interrupted by user")
    except Exception as e:
        logger.error(f"Trading failed: {e}", exc_info=True)
        raise


async def _run_backtest(config, strategy_name: str, emit=click.echo):
    """Run backtest."""
    logger = logging.getLogger(__name__)

    try:
        symbol = config.symbols[0]
        data_feed = create_data_feed_from_config()
        market_data = MarketData(data_feed)
        history_limit = max(config.strategy.lookback_period * 3, config.data.historical_days * 24 * 60)
        history = await market_data.get_ohlcv(
            symbol=symbol,
            timeframe='1m',
            limit=history_limit,
            use_cache=False,
        )

        if strategy_name == 'ai':
            strategy = AIStrategy()
        else:
            from crypto_trader.strategy.base import DummyStrategy
            strategy = DummyStrategy()

        backtest = BacktestEngine(
            config=config,
            strategy=strategy,
            historical_data={symbol: history},
            initial_balance=10000.0,
        )
        result = await backtest.run()
        report_dir = _ensure_reports_dir(BACKTEST_REPORTS_DIR)
        report_path = report_dir / f"{_safe_symbol(symbol)}_{strategy_name}_{_timestamp_slug()}.json"
        trades_path = report_dir / f"{report_path.stem}_trades.csv"
        report_payload = {
            "generated_at": datetime.now().isoformat(),
            "strategy": strategy_name,
            "report_type": "backtest",
            **result.to_dict(),
        }
        if backtest.exchange.trade_history:
            report_payload["trade_count_from_history"] = len(backtest.exchange.trade_history)
            report_payload["trades_csv"] = str(trades_path)
            _write_csv_report(trades_path, backtest.exchange.trade_history)

        report_path.write_text(
            json.dumps(report_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        emit(f"\n{'=' * 56}")
        emit(f"  Backtest Complete - {result.symbol}")
        emit(f"{'=' * 56}")
        emit(f"Period: {result.start_time} -> {result.end_time}")
        emit(f"Candles: {result.candles} | Warmup: {result.warmup_candles}")
        emit(f"Initial Balance: {result.initial_balance:.2f} USDT")
        emit(f"Final Equity:    {result.final_equity:.2f} USDT")
        emit(f"Total PnL:       {result.total_pnl:+.2f} USDT")
        emit(f"Strategy Return: {result.total_return_pct:+.2f}%")
        emit(f"Buy&Hold Return: {result.buy_and_hold_return_pct:+.2f}%")
        emit(f"Max Drawdown:    {result.max_drawdown_pct:.2f}%")
        emit(f"Trades: {result.trade_count} | Signals: {result.signal_count}")
        emit(
            f"Closed Positions: {result.total_closed} | Wins: {result.win_count} | "
            f"Losses: {result.loss_count} | Win Rate: {result.win_rate:.2%}"
        )
        emit(f"Open Positions at End: {result.position_count}")
        emit(f"Report: {report_path}")
        if backtest.exchange.trade_history:
            emit(f"Trades:  {trades_path}")
        emit(f"{'=' * 56}\n")

        return {
            "result": result,
            "report_path": report_path,
            "trades_path": trades_path if backtest.exchange.trade_history else None,
        }
    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        raise


async def _run_training(config, symbol: str, period: str, emit=click.echo):
    """Train AI model."""
    logger = logging.getLogger(__name__)

    try:
        data_feed = create_data_feed_from_config()
        market_data = MarketData(data_feed)
        strategy = AIStrategy()
        lookback_limit = max(config.strategy.lookback_period * 3, _period_to_minutes(period))

        logger.info(f"Fetching {period} of historical data for {symbol} (limit={lookback_limit})")
        emit(f"Training AI model for {symbol} with {period} of data...")

        history = await market_data.get_ohlcv(
            symbol=symbol,
            timeframe='1m',
            limit=lookback_limit,
            use_cache=False,
        )

        df_features = strategy.feature_engine.calculate_features(history)
        X, y = strategy.feature_engine.prepare_training_data(df_features)
        metrics = strategy.ai_model.train(X, y, strategy.feature_engine.feature_columns)

        if not metrics.get("success"):
            raise RuntimeError(metrics.get("error", "Training failed"))

        feature_importance = strategy.feature_engine.get_feature_importance(strategy.ai_model.model)
        top_features = sorted(
            feature_importance.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:10]

        report_dir = _ensure_reports_dir(TRAINING_REPORTS_DIR)
        report_path = report_dir / f"{_safe_symbol(symbol)}_{_timestamp_slug()}.json"
        report_payload = {
            "generated_at": datetime.now().isoformat(),
            "report_type": "training",
            "symbol": symbol,
            "period": period,
            "candles_fetched": len(history),
            "feature_rows": len(df_features),
            "feature_count": len(strategy.feature_engine.feature_columns),
            "model_path": str(strategy.ai_model.model_path),
            "metrics": metrics,
            "top_features": [
                {"feature": name, "importance": importance}
                for name, importance in top_features
            ],
        }
        report_path.write_text(
            json.dumps(report_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        emit(f"Training completed successfully!")
        emit(f"Samples: train={metrics['train_size']} test={metrics['test_size']}")
        emit(
            f"Metrics: accuracy={metrics['accuracy']:.2%}, "
            f"precision={metrics['precision']:.2%}, "
            f"recall={metrics['recall']:.2%}, "
            f"f1={metrics['f1']:.2%}"
        )
        emit(f"Model:  {strategy.ai_model.model_path}")
        emit(f"Report: {report_path}")
        return {
            "metrics": metrics,
            "report_path": report_path,
            "model_path": strategy.ai_model.model_path,
        }

    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        raise


async def _run_research(config, symbol: str, period: str, days: int, strategy: str, emit=click.echo):
    """Train first, then backtest using the updated model."""
    emit(f"\n{'=' * 56}")
    emit(f"  Research Workflow - {symbol}")
    emit(f"{'=' * 56}")

    training = await _run_training(config, symbol, period, emit=emit)
    backtest = await _run_backtest(config, strategy, emit=emit)

    emit("Research summary:")
    emit(f"Training report: {training['report_path']}")
    emit(f"Backtest report: {backtest['report_path']}")
    if backtest.get("trades_path"):
        emit(f"Trades CSV:      {backtest['trades_path']}")
    emit(f"{'=' * 56}\n")
    return {
        "training": training,
        "backtest": backtest,
    }


def main():
    """Main entry point."""
    cli(obj={})


if __name__ == '__main__':
    main()
