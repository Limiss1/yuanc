import asyncio
import logging
from crypto_trader.infra.config import load_config
from crypto_trader.data.market_data import create_data_feed_from_config, MarketData
from crypto_trader.execution.paper_exchange import PaperExchange
from crypto_trader.execution.trading_engine import TradingEngine
from crypto_trader.strategy.ai_strategy import AIStrategy
from crypto_trader.risk.risk_manager import RiskManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def test():
    config = load_config()
    data_feed = create_data_feed_from_config()
    market_data = MarketData(data_feed)
    exchange = PaperExchange(initial_balance={"USDT": 10000.0}, default_leverage=10)
    strategy = AIStrategy()
    risk_manager = RiskManager()
    engine = TradingEngine(config=config, strategy=strategy, exchange=exchange, market_data=market_data, risk_manager=risk_manager)
    
    print("Initializing balance...")
    await engine._initialize_balance()
    balance = await exchange.get_balance()
    print(f"Balance: {balance}")
    
    print("Running 1 cycle...")
    await engine._trading_cycle()
    
    print("Refreshing prices...")
    await engine.refresh_prices()
    
    summary = exchange.get_portfolio_summary()
    print(f"Equity: {summary['equity']:.2f}")
    print(f"Unrealized PnL: {summary['unrealized_pnl']:.4f}")
    print(f"Positions: {summary['position_count']}")
    for pos in summary['positions']:
        print(f"  {pos['symbol']}: {pos['side']} entry={pos['entry_price']:.2f} current={pos['current_price']:.2f} pnl={pos['unrealized_pnl']:.4f}")
    print("Done!")

asyncio.run(test())
