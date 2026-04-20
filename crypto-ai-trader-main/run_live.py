import argparse
import asyncio
import logging
import os
import signal as signal_module
import sys
import time
from datetime import datetime

from crypto_trader.infra.config import load_config, set_config, MarketMode
from crypto_trader.data.market_data import create_data_feed_from_config, MarketData
from crypto_trader.execution.exchange import create_exchange_from_config
from crypto_trader.execution.trading_engine import TradingEngine
from crypto_trader.strategy.ai_strategy import AIStrategy
from crypto_trader.risk.risk_manager import RiskManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('live_trading.log', encoding='utf-8', mode='a')
    ]
)

logger = logging.getLogger(__name__)

PID_FILE = 'live_trading.pid'
_shutdown = False


def signal_handler(signum, frame):
    global _shutdown
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    _shutdown = True


def kill_old_processes():
    my_pid = os.getpid()
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                old_pid = f.read().strip()
            if old_pid:
                old_pid = int(old_pid)
                if old_pid != my_pid:
                    try:
                        os.kill(old_pid, 9)
                        logger.info(f"Killed old process PID {old_pid}")
                        time.sleep(2)
                    except (OSError, ProcessLookupError):
                        pass
        except (ValueError, OSError):
            pass
    try:
        import subprocess
        result = subprocess.run(
            ['wmic', 'process', 'where', "commandline like '%run_live%'", 'get', 'processid'],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split('\n'):
            line = line.strip()
            if line.isdigit() and int(line) != my_pid:
                try:
                    os.kill(int(line), 9)
                    logger.info(f"Killed stale run_live process PID {line}")
                except (OSError, ProcessLookupError):
                    pass
    except Exception:
        pass


def write_pid():
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))


def remove_pid():
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                stored_pid = f.read().strip()
            if stored_pid == str(os.getpid()):
                os.remove(PID_FILE)
    except Exception:
        pass


def parse_args():
    parser = argparse.ArgumentParser(description="Crypto AI Trader - Live Trading System")
    parser.add_argument(
        '--mode', '-m',
        choices=['testnet', 'live'],
        default=None,
        help="Trading environment: 'testnet' (simulated) or 'live' (real money). Overrides config.yaml trading_mode."
    )
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help="Skip confirmation prompt for live mode"
    )
    return parser.parse_args()


async def main():
    args = parse_args()

    signal_module.signal(signal_module.SIGINT, signal_handler)
    signal_module.signal(signal_module.SIGTERM, signal_handler)

    kill_old_processes()
    write_pid()

    config = load_config()

    if args.mode:
        config.trading_mode = MarketMode(args.mode)
        config.apply_market_mode()
        set_config(config)

    is_live = config.trading_mode == MarketMode.LIVE

    if is_live:
        logger.warning("=" * 60)
        logger.warning("  *** LIVE TRADING MODE - REAL MONEY AT RISK ***")
        logger.warning("=" * 60)
        if not args.yes:
            try:
                confirm = input("  Are you sure you want to trade with REAL money? (type 'YES' to confirm): ")
                if confirm.strip() != 'YES':
                    logger.info("Live mode cancelled by user.")
                    remove_pid()
                    return
            except (EOFError, KeyboardInterrupt):
                logger.info("Live mode cancelled.")
                remove_pid()
                return

    mode_label = "LIVE (Real Money)" if is_live else "TESTNET (Simulated)"

    logger.info("=" * 60)
    logger.info(f"  Trading System Starting - {mode_label}")
    logger.info(f"  PID: {os.getpid()}")
    logger.info(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  Market Mode: {config.trading_mode.value}")
    logger.info(f"  Testnet: {config.exchange.testnet}")
    logger.info(f"  API Key: {config.exchange.api_key[:8]}..." if config.exchange.api_key else "  API Key: None")
    logger.info("=" * 60)

    data_feed = create_data_feed_from_config()
    market_data = MarketData(data_feed)
    exchange = create_exchange_from_config()
    strategy = AIStrategy()
    risk_manager = RiskManager()
    engine = TradingEngine(
        config=config,
        strategy=strategy,
        exchange=exchange,
        market_data=market_data,
        risk_manager=risk_manager
    )

    logger.info(f"Mode: {mode_label}")
    logger.info(f"Symbols: {config.symbols}")
    logger.info(f"Leverage: {config.exchange.leverage}x")
    logger.info(f"Confidence threshold: {engine.confidence_threshold:.0%}")
    logger.info(f"Win rate threshold for retrain: {engine._win_rate_threshold:.0%}")

    try:
        await engine.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        engine.stop()
        remove_pid()
        logger.info("Trading system stopped gracefully.")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        remove_pid()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        remove_pid()
