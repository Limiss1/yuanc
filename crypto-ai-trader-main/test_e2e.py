import sys
sys.path.insert(0, r"c:\Users\ll552\Desktop\8项修复\crypto-ai-trader-main")

lines = []

async def debug_signal():
    from crypto_trader.infra.config import load_config, TradingMode
    from crypto_trader.data.market_data import create_data_feed_from_config, MarketData
    from crypto_trader.strategy.ai_strategy import AIStrategy
    from crypto_trader.strategy.base import SignalType

    config = load_config()
    config.mode = TradingMode.PAPER_TRADING
    config.symbols = ["BTC/USDT"]

    data_feed = create_data_feed_from_config()
    market_data = MarketData(data_feed)
    strategy = AIStrategy()

    lines.append(f"Confidence threshold: {strategy.confidence_threshold}")

    signal = await strategy.analyze(market_data, "BTC/USDT")

    lines.append(f"Signal type: {signal.signal_type.value}")
    lines.append(f"Signal type enum: {signal.signal_type}")
    lines.append(f"Confidence: {signal.confidence:.4f}")
    lines.append(f"Price: {signal.price:.2f}")
    lines.append(f"Metadata: {signal.metadata}")

    lines.append(f"Is BUY: {signal.signal_type == SignalType.BUY}")
    lines.append(f"Is SELL: {signal.signal_type == SignalType.SELL}")
    lines.append(f"Is HOLD: {signal.signal_type == SignalType.HOLD}")

    if signal.signal_type == SignalType.HOLD:
        lines.append("")
        lines.append("Signal is HOLD - checking why...")
        lines.append(f"Model loaded: {strategy.ai_model.model is not None}")

        df = await market_data.get_technical_indicators("BTC/USDT", limit=500)
        lines.append(f"Data rows: {len(df)}")

        from crypto_trader.strategy.ai_strategy import FeatureEngine
        import numpy as np
        fe = strategy.feature_engine
        df_features = fe.calculate_features(df)
        lines.append(f"Features rows: {len(df_features)}")
        lines.append(f"Feature columns: {len(fe.feature_columns)}")

        if len(df_features) > 0:
            latest = df_features.iloc[-1]
            feature_values = np.array([latest[col] for col in fe.feature_columns])
            lines.append(f"Feature values shape: {feature_values.shape}")
            lines.append(f"NaN count: {np.isnan(feature_values).sum()}")

            prediction, confidence = strategy.ai_model.predict(feature_values)
            lines.append(f"Raw prediction: {prediction}")
            lines.append(f"Raw confidence: {confidence:.4f}")

            lines.append(f"predict_proba result: {strategy.ai_model.model.predict_proba(feature_values.reshape(1, -1))}")

import asyncio
asyncio.run(debug_signal())

with open(r"c:\Users\ll552\Desktop\8项修复\test_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
