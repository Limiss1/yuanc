import csv
from pathlib import Path

from crypto_trader.cli.main import _period_to_minutes, _safe_symbol
from crypto_trader.cli.main import _write_csv_report


def test_period_to_minutes_supports_common_units():
    assert _period_to_minutes("30m") == 30
    assert _period_to_minutes("2h") == 120
    assert _period_to_minutes("7d") == 10080


def test_safe_symbol_normalizes_futures_symbol():
    assert _safe_symbol("BTC/USDT:USDT") == "BTC-USDT-USDT"


def test_write_csv_report_persists_rows():
    path = Path(__file__).resolve().parent / "_tmp_cli_report.csv"
    rows = [
        {"symbol": "BTC/USDT:USDT", "side": "buy", "price": 100.0},
        {"symbol": "BTC/USDT:USDT", "side": "sell", "price": 101.0},
    ]

    try:
        _write_csv_report(path, rows)

        with open(path, "r", encoding="utf-8", newline="") as handle:
            reader = list(csv.DictReader(handle))

        assert len(reader) == 2
        assert reader[0]["side"] == "buy"
        assert reader[1]["price"] == "101.0"
    finally:
        path.unlink(missing_ok=True)
