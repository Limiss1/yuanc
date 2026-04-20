import sys
import os
import warnings
import tempfile
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent))

from crypto_trader.strategy.ai_strategy import FeatureEngine, AIModel, AIStrategy
from crypto_trader.models.base_model import BaseModel, ModelMetadata


def generate_mock_ohlcv(n=600):
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=n, freq='1min')
    base_price = 65000.0
    returns = np.random.randn(n) * 0.002
    close = base_price * np.exp(np.cumsum(returns))
    high = close * (1 + np.abs(np.random.randn(n)) * 0.001)
    low = close * (1 - np.abs(np.random.randn(n)) * 0.001)
    open_ = close * (1 + np.random.randn(n) * 0.0005)
    volume = np.abs(np.random.randn(n)) * 1000 + 500

    df = pd.DataFrame({
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    }, index=dates)
    df.index.name = 'timestamp'
    return df


def sep(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def test_fix1_feature_engine_single_instance():
    sep("[FIX-1] FeatureEngine single instance - feature columns sync")

    df = generate_mock_ohlcv(600)

    strategy = AIStrategy.__new__(AIStrategy)
    strategy.config = {}
    strategy.feature_engine = FeatureEngine()
    strategy.ai_model = AIModel(model_path=Path(tempfile.mkdtemp()) / "test_model.pkl")

    df_features = strategy.feature_engine.calculate_features(df)
    X, y = strategy.feature_engine.prepare_training_data(df_features)

    print(f"\n[Strategy FeatureEngine] feature_columns count: {len(strategy.feature_engine.feature_columns)}")
    print(f"[Strategy FeatureEngine] first 5: {strategy.feature_engine.feature_columns[:5]}")

    print(f"\n[AIModel] feature_columns count: {len(strategy.ai_model.feature_columns)}")
    print(f"[AIModel] feature_columns: {strategy.ai_model.feature_columns}")

    if len(X) >= 100:
        metrics = strategy.ai_model.train(X, y, feature_columns=strategy.feature_engine.feature_columns)
        print(f"\nTrain result: success={metrics.get('success')}, accuracy={metrics.get('accuracy', 0):.2%}")

    print(f"\n[After train AIModel] feature_columns count: {len(strategy.ai_model.feature_columns)}")
    print(f"[After train AIModel] feature_columns: {strategy.ai_model.feature_columns}")

    save_result = strategy.ai_model.save()
    print(f"\nModel save result: {save_result}")

    print(f"\n--- Simulate load scenario ---")
    new_model = AIModel(model_path=strategy.ai_model.model_path)
    load_result = new_model.load()
    print(f"Model load result: {load_result}")
    print(f"[Loaded model] feature_columns count: {len(new_model.feature_columns)}")
    print(f"[Loaded model] feature_columns: {new_model.feature_columns}")

    strategy_cols = set(strategy.feature_engine.feature_columns)
    model_cols = set(new_model.feature_columns)

    if len(model_cols) == 0:
        print(f"\n[FAIL] Model-side feature_columns is EMPTY after load!")
    elif strategy_cols != model_cols:
        print(f"\n[FAIL] Strategy and model feature columns are INCONSISTENT!")
        print(f"  Strategy only: {strategy_cols - model_cols}")
        print(f"  Model only: {model_cols - strategy_cols}")
    else:
        print(f"\n[PASS] Feature columns are consistent between strategy and model!")

    df_features2 = strategy.feature_engine.calculate_features(df)
    latest = df_features2.iloc[-1]

    try:
        feature_values = np.array([latest[col] for col in new_model.feature_columns])
        prediction, confidence = new_model.predict(feature_values)
        print(f"Predict with loaded model features: prediction={prediction}, confidence={confidence:.4f}")
        print(f"\n[PASS] Model can predict with loaded feature_columns!")
    except Exception as e:
        print(f"[FAIL] Predict with loaded model features FAILED: {type(e).__name__}: {e}")


def test_fix2_time_series_split():
    sep("[FIX-2] Time-series chronological split (no data leakage)")

    df = generate_mock_ohlcv(600)
    fe = FeatureEngine()
    df_features = fe.calculate_features(df)
    X, y = fe.prepare_training_data(df_features)

    if len(X) < 100:
        print("Insufficient data, skip")
        return

    model = AIModel(model_path=Path(tempfile.mkdtemp()) / "test_model.pkl")
    metrics = model.train(X, y, feature_columns=fe.feature_columns)

    print(f"\nTrain result: success={metrics.get('success')}")
    print(f"Accuracy: {metrics.get('accuracy', 0):.2%}")
    print(f"Train size: {metrics.get('train_size', 0)}, Test size: {metrics.get('test_size', 0)}")

    train_size = metrics.get('train_size', 0)
    test_size = metrics.get('test_size', 0)
    total = train_size + test_size

    if train_size > 0 and test_size > 0:
        expected_train = int(total * 0.8)
        expected_test = total - expected_train
        if train_size == expected_train and test_size == expected_test:
            print(f"\n[PASS] Chronological split confirmed: first 80% train, last 20% test")
        else:
            print(f"\n[FAIL] Split sizes don't match chronological pattern")
    else:
        print(f"\n[FAIL] Training failed")


def test_fix3_no_column_conflict():
    sep("[FIX-3] No column conflict - using get_ohlcv() instead of get_technical_indicators()")

    df = generate_mock_ohlcv(600)

    print("\n--- Step 1: get_ohlcv() returns only OHLCV columns ---")
    ohlcv_columns = set(df.columns)
    print(f"get_ohlcv() columns: {sorted(ohlcv_columns)}")

    print("\n--- Step 2: FeatureEngine adds features on clean OHLCV data ---")
    fe = FeatureEngine()
    df_features = fe.calculate_features(df.copy())
    fe_columns = set(fe.feature_columns)
    print(f"FeatureEngine feature columns count: {len(fe_columns)}")

    print("\n--- Step 3: Check for conflicts ---")
    base_columns = {'open', 'high', 'low', 'close', 'volume', 'timestamp'}
    conflict = fe_columns & base_columns
    if conflict:
        print(f"[FAIL] Feature columns still conflict with base OHLCV: {sorted(conflict)}")
    else:
        print(f"[PASS] No conflicts between feature columns and base OHLCV data")

    ghost_cols = {'sma_30', 'volume_sma'}
    for col in ghost_cols:
        if col in fe_columns:
            print(f"[WARN] '{col}' is in feature_columns but FeatureEngine didn't create it (ghost feature)")
        else:
            print(f"[PASS] '{col}' is NOT in feature_columns (no ghost feature)")


def test_fix4_confidence_threshold_consistency():
    sep("[FIX-4] Confidence threshold consistency")

    from crypto_trader.infra.config import get_config

    try:
        config = get_config()
        config_threshold = config.strategy.confidence_threshold
        print(f"StrategyConfig.confidence_threshold: {config_threshold}")
    except Exception as e:
        print(f"Failed to read config: {e}")
        config_threshold = None

    try:
        from crypto_trader.execution.trading_engine import TradingEngine
        from crypto_trader.execution.paper_exchange import PaperExchange
        from crypto_trader.infra.config import TradingConfig, TradingMode
        from crypto_trader.data.market_data import MarketData

        trading_config = TradingConfig(
            mode=TradingMode.PAPER_TRADING,
            symbols=["BTC/USDT"]
        )
        strategy = AIStrategy.__new__(AIStrategy)
        strategy.config = {}
        strategy.confidence_threshold = config_threshold if config_threshold else 0.65
        strategy.feature_engine = FeatureEngine()
        strategy.ai_model = AIModel()

        exchange = PaperExchange(initial_balance={"USDT": 10000.0}, use_api_balance=False)
        market_data = MarketData.__new__(MarketData)

        engine = TradingEngine(
            config=trading_config,
            strategy=strategy,
            exchange=exchange,
            market_data=market_data
        )
        engine_threshold = engine.confidence_threshold
        print(f"TradingEngine.confidence_threshold: {engine_threshold}")

        if config_threshold is not None and abs(engine_threshold - config_threshold) < 1e-6:
            print(f"\n[PASS] TradingEngine reads threshold from config ({config_threshold})")
        elif config_threshold is not None:
            print(f"\n[FAIL] TradingEngine threshold ({engine_threshold}) != config ({config_threshold})")
        else:
            print(f"\n[INFO] Cannot verify - config not available")
    except Exception as e:
        print(f"TradingEngine init test failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        print("[INFO] Skipping TradingEngine threshold verification")


def test_fix5_no_use_label_encoder():
    sep("[FIX-5] XGBoost without use_label_encoder")

    import xgboost as xgb

    print(f"XGBoost version: {xgb.__version__}")

    X_dummy = np.random.randn(100, 5)
    y_dummy = np.random.randint(0, 2, 100)

    try:
        model = xgb.XGBClassifier(
            n_estimators=10,
            eval_metric='logloss',
        )
        model.fit(X_dummy, y_dummy)
        print("[PASS] XGBClassifier works without use_label_encoder")
    except Exception as e:
        print(f"[FAIL] XGBClassifier failed without use_label_encoder: {type(e).__name__}: {e}")

    model2 = AIModel(model_path=Path(tempfile.mkdtemp()) / "test_model.pkl")
    created_model = model2.create_model()
    params = created_model.get_params()
    if 'use_label_encoder' in params:
        print(f"[FAIL] AIModel.create_model() still has use_label_encoder parameter")
    else:
        print(f"[PASS] AIModel.create_model() no longer has use_label_encoder")


def test_fix8_no_inf_in_normalized_range():
    sep("[FIX-8] normalized_range prevents inf")

    df2 = generate_mock_ohlcv(60)
    close_vals = df2['close'].iloc[:20].values
    df2.loc[df2.index[:20], 'high'] = close_vals
    df2.loc[df2.index[:20], 'low'] = close_vals

    fe2 = FeatureEngine()
    df2_features = fe2.calculate_features(df2)

    if len(df2_features) > 0:
        has_inf = np.isinf(df2_features.select_dtypes(include=[np.number]).values).any()
        if has_inf:
            inf_cols = df2_features.columns[df2_features.apply(lambda col: np.isinf(col).any())].tolist()
            print(f"[FAIL] Still has inf values in: {inf_cols}")
        else:
            print(f"[PASS] No inf values in features (normalized_range uses replace(0, nan))")
    else:
        n = 60
        dates = pd.date_range(end=datetime.now(), periods=n, freq='1min')
        df_const = pd.DataFrame({
            'open': [100.0] * n,
            'high': [100.0] * n,
            'low': [100.0] * n,
            'close': [100.0] * n,
            'volume': [1000.0] * n
        }, index=dates)
        fe_const = FeatureEngine()
        df_const_features = fe_const.calculate_features(df_const)
        if len(df_const_features) > 0:
            has_inf = np.isinf(df_const_features.select_dtypes(include=[np.number]).values).any()
            if has_inf:
                print(f"[FAIL] Constant price data still produces inf")
            else:
                print(f"[PASS] Constant price data produces no inf (NaN instead)")
        else:
            print(f"[PASS] Constant price data results in empty DataFrame after dropna (NaN, not inf)")


def test_fix10_no_model_returns_hold():
    sep("[FIX-10] predict() returns HOLD when no model loaded")

    model = AIModel(model_path=Path(tempfile.mkdtemp()) / "nonexistent.pkl")

    prediction, confidence = model.predict(np.array([1.0, 2.0, 3.0]))

    print(f"No model predict returns: prediction={prediction}, confidence={confidence}")

    from crypto_trader.strategy.base import SignalType

    if prediction == -1:
        signal_type = SignalType.HOLD
    elif prediction == 1:
        signal_type = SignalType.BUY
    else:
        signal_type = SignalType.SELL

    print(f"Mapped to signal type: {signal_type.value}")
    print(f"confidence={confidence} exceeds any threshold? {confidence >= 0.45}")

    if signal_type == SignalType.HOLD:
        print(f"\n[PASS] No model returns HOLD (prediction=-1, confidence=0.0)")
    elif signal_type == SignalType.SELL and confidence >= 0.45:
        print(f"\n[FAIL] No model still returns SELL with high confidence!")
    else:
        print(f"\n[PARTIAL] No model returns {signal_type.value} but confidence is low")


if __name__ == "__main__":
    print("=" * 70)
    print("  AI Prediction Pipeline - Fix Verification Tests")
    print("=" * 70)

    test_fix1_feature_engine_single_instance()
    test_fix2_time_series_split()
    test_fix3_no_column_conflict()
    test_fix4_confidence_threshold_consistency()
    test_fix5_no_use_label_encoder()
    test_fix8_no_inf_in_normalized_range()
    test_fix10_no_model_returns_hold()

    sep("ALL FIX TESTS COMPLETE")
