import asyncio
import sys
import numpy as np
from crypto_trader.infra.config import load_config
from crypto_trader.data.market_data import create_data_feed_from_config, MarketData
from crypto_trader.strategy.ai_strategy import AIStrategy

output = []

async def test():
    config = load_config()
    data_feed = create_data_feed_from_config()
    market_data = MarketData(data_feed)
    strategy = AIStrategy()

    output.append('=== Real-time Prediction Test ===')
    output.append(f'Feature engine columns ({len(strategy.feature_engine.feature_columns)}): {strategy.feature_engine.feature_columns}')
    output.append(f'Model feature columns ({len(strategy.ai_model.feature_columns)}): {strategy.ai_model.feature_columns}')
    match = len(strategy.feature_engine.feature_columns) == len(strategy.ai_model.feature_columns)
    output.append(f'Feature count match: {match}')
    if not match:
        output.append('[WARN] Feature count mismatch! This will cause prediction errors.')
    output.append('')

    for symbol in config.symbols:
        try:
            df = await market_data.get_ohlcv(symbol=symbol, timeframe='1m', limit=500)
            output.append(f'--- {symbol} ---')
            output.append(f'  Data points: {len(df)}')
            last_close = df.iloc[-1]['close']
            output.append(f'  Latest price: {last_close:.2f}')

            df_features = strategy.feature_engine.calculate_features(df)
            output.append(f'  Feature rows after dropna: {len(df_features)}')

            if len(df_features) > 0:
                latest = df_features.iloc[-1]
                feature_values = np.array([latest[col] for col in strategy.feature_engine.feature_columns])
                output.append(f'  Feature vector length: {len(feature_values)}')

                prediction, confidence = strategy.ai_model.predict(feature_values)
                pred_str = {1: 'BUY', 0: 'SELL', -1: 'ERROR'}.get(prediction, 'UNKNOWN')
                output.append(f'  Prediction: {prediction} ({pred_str})')
                output.append(f'  Confidence: {confidence:.4f} ({confidence:.2%})')
                output.append(f'  Threshold: {strategy.confidence_threshold:.0%}')
                would_trade = confidence >= strategy.confidence_threshold and prediction != -1
                output.append(f'  Would trade: {would_trade}')
            else:
                output.append(f'  [WARN] Not enough data for features')
            output.append('')
        except Exception as e:
            output.append(f'  [ERROR] {e}')
            import traceback
            tb = traceback.format_exc()
            output.append(tb)

    output.append('=== Model Accuracy ===')
    if strategy.ai_model.accuracy_history:
        for i, acc in enumerate(strategy.ai_model.accuracy_history):
            output.append(f'  Training #{i+1}: accuracy={acc:.2%}')
        output.append(f'  Current accuracy: {strategy.ai_model.accuracy_history[-1]:.2%}')
        output.append(f'  Win rate threshold for retrain: 80%')
        if strategy.ai_model.accuracy_history[-1] < 0.80:
            output.append(f'  [INFO] Accuracy below 80%, model will auto-retrain after more trades')
    else:
        output.append('  No accuracy history')

    with open('test_model_result.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))

asyncio.run(test())
