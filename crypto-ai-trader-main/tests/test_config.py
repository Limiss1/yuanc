"""
Tests for configuration management.
"""

import os
from pathlib import Path

import pytest

from crypto_trader.infra.config import (
    TradingConfig, ExchangeConfig, StrategyConfig, RiskConfig, DataConfig,
    ExchangeType, TradingMode, load_config
)


class TestExchangeConfig:
    """Test exchange configuration."""
    
    def test_default_values(self):
        """Test default values."""
        config = ExchangeConfig()
        
        assert config.name == ExchangeType.BINANCE
        assert config.api_key is None
        assert config.api_secret is None
        assert config.testnet is True
    
    def test_from_env(self):
        """Test loading from environment variables."""
        os.environ['EXCHANGE_NAME'] = 'binance'
        os.environ['EXCHANGE_API_KEY'] = 'test_key'
        os.environ['EXCHANGE_API_SECRET'] = 'test_secret'
        os.environ['EXCHANGE_TESTNET'] = 'false'
        
        config = ExchangeConfig()
        
        assert config.name == ExchangeType.BINANCE
        assert config.api_key == 'test_key'
        assert config.api_secret == 'test_secret'
        assert config.testnet is False
        
        # Clean up
        del os.environ['EXCHANGE_NAME']
        del os.environ['EXCHANGE_API_KEY']
        del os.environ['EXCHANGE_API_SECRET']
        del os.environ['EXCHANGE_TESTNET']


class TestStrategyConfig:
    """Test strategy configuration."""
    
    def test_default_values(self):
        """Test default values."""
        config = StrategyConfig()
        
        assert config.name == 'ai'
        assert config.confidence_threshold == 0.6
        assert config.max_position_size == 0.1
        assert config.lookback_period == 500


class TestRiskConfig:
    """Test risk configuration."""
    
    def test_default_values(self):
        """Test default values."""
        config = RiskConfig()
        
        assert config.max_drawdown == 0.15
        assert config.daily_loss_limit == 0.05
        assert config.max_open_positions == 3
        assert config.stop_loss_pct == 0.0015
        assert config.take_profit_pct == 0.003


class TestDataConfig:
    """Test data configuration."""
    
    def test_default_values(self):
        """Test default values."""
        config = DataConfig()
        
        assert config.cache_dir == Path.home() / ".crypto_trader" / "cache"
        assert config.historical_days == 30
        assert config.update_interval == 60
        assert config.save_raw_data is False


class TestTradingConfig:
    """Test main trading configuration."""

    @staticmethod
    def _write_local_config(filename: str, content: str) -> Path:
        path = Path(__file__).resolve().parent / filename
        path.write_text(content, encoding="utf-8")
        return path
    
    def test_default_values(self):
        """Test default values."""
        config = TradingConfig()
        
        assert config.mode == TradingMode.PAPER_TRADING
        assert config.symbols == ["BTC/USDT:USDT", "ETH/USDT:USDT"]
        assert config.base_currency == "USDT"
        
        # Check nested configs
        assert isinstance(config.exchange, ExchangeConfig)
        assert isinstance(config.strategy, StrategyConfig)
        assert isinstance(config.risk, RiskConfig)
        assert isinstance(config.data, DataConfig)
    
    def test_from_yaml(self):
        """Test loading from YAML file."""
        yaml_content = """
mode: "backtest"
symbols: ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
base_currency: "USDT"
exchange:
  name: "binance"
  testnet: true
strategy:
  name: "ai"
  confidence_threshold: 0.7
risk:
  max_drawdown: 0.1
  daily_loss_limit: 0.03
data:
  cache_dir: "/tmp/test_cache"
  historical_days: 60
"""
        config_path = self._write_local_config("_tmp_trading_config.yaml", yaml_content)
        try:
            config = TradingConfig.from_yaml(config_path)

            assert config.mode == TradingMode.BACKTEST
            assert config.symbols == ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
            assert config.exchange.name == ExchangeType.BINANCE
            assert config.exchange.testnet is True
            assert config.strategy.confidence_threshold == 0.7
            assert config.risk.max_drawdown == 0.1
            assert config.data.historical_days == 60
        finally:
            config_path.unlink(missing_ok=True)
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = TradingConfig()
        config_dict = config.to_dict()
        
        assert 'mode' in config_dict
        assert 'symbols' in config_dict
        assert 'exchange' in config_dict
        assert 'strategy' in config_dict
        assert 'risk' in config_dict
        assert 'data' in config_dict


class TestLoadConfig:
    """Test configuration loading."""
    
    def test_load_default(self):
        """Test loading default configuration."""
        config = load_config()
        
        assert isinstance(config, TradingConfig)
        assert isinstance(config.mode, TradingMode)
    
    def test_load_from_file(self):
        """Test loading from YAML file."""
        yaml_content = """
mode: "backtest"
symbols: ["BTC/USDT"]
"""
        config_path = Path(__file__).resolve().parent / "_tmp_load_config.yaml"
        config_path.write_text(yaml_content, encoding="utf-8")
        try:
            config = load_config(config_path)

            assert config.mode == TradingMode.BACKTEST
            assert config.symbols == ["BTC/USDT"]
        finally:
            config_path.unlink(missing_ok=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
