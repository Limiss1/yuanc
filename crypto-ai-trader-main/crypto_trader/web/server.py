"""
aiohttp web dashboard for Crypto Trader workflows and reports.
"""

from __future__ import annotations

import asyncio
import csv
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from aiohttp import web

from ..cli.main import (
    BACKTEST_REPORTS_DIR,
    TRAINING_REPORTS_DIR,
    _run_backtest,
    _run_research,
    _run_training,
)
from ..data.market_data import MarketData, create_data_feed_from_config
from ..execution.exchange import create_exchange_from_config
from ..execution.paper_exchange import PaperExchange
from ..execution.trading_engine import TradingEngine
from ..infra.config import MarketMode, TradingMode, load_config, set_config
from ..risk.risk_manager import RiskManager
from ..strategy.ai_strategy import AIStrategy


WEB_ROOT = Path(__file__).resolve().parent / "static"
MAX_LOG_LINES = 120


def _json_response(payload: Any, status: int = 200) -> web.Response:
    return web.json_response(payload, status=status, dumps=lambda obj: json.dumps(obj, ensure_ascii=False))


def _safe_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def _read_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_csv(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _collect_reports(directory: Path, limit: int = 12) -> List[Dict[str, Any]]:
    if not directory.exists():
        return []

    reports = []
    for path in sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]:
        try:
            payload = _read_json(path)
            reports.append(
                {
                    "name": path.name,
                    "path": _safe_path(path),
                    "updated_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                    "payload": payload,
                }
            )
        except Exception as exc:
            reports.append(
                {
                    "name": path.name,
                    "path": _safe_path(path),
                    "updated_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                    "error": str(exc),
                }
            )
    return reports


def _overview_payload() -> Dict[str, Any]:
    training_reports = _collect_reports(TRAINING_REPORTS_DIR)
    backtest_reports = _collect_reports(BACKTEST_REPORTS_DIR)
    latest_training = training_reports[0]["payload"] if training_reports else None
    latest_backtest = backtest_reports[0]["payload"] if backtest_reports else None

    return {
        "generated_at": datetime.now().isoformat(),
        "training_reports": training_reports,
        "backtest_reports": backtest_reports,
        "latest_training": latest_training,
        "latest_backtest": latest_backtest,
    }


def _trading_status_payload(session: Dict[str, Any]) -> Dict[str, Any]:
    engine = session.get("engine")
    if not engine:
        return {
            "running": False,
            "mode": session.get("mode", "paper"),
            "symbol": session.get("symbol", "BTC/USDT:USDT"),
            "logs": session.get("logs", []),
        }

    status = engine.get_status()
    status.update(
        {
            "running": bool(session.get("task")) and not session["task"].done(),
            "mode": session.get("mode", "paper"),
            "symbol": session.get("symbol", "BTC/USDT:USDT"),
            "logs": session.get("logs", []),
            "started_at": session.get("started_at"),
        }
    )
    return status


async def _handle_index(_: web.Request) -> web.FileResponse:
    return web.FileResponse(WEB_ROOT / "index.html")


async def _handle_overview(_: web.Request) -> web.Response:
    return _json_response(_overview_payload())


async def _handle_report(request: web.Request) -> web.Response:
    kind = request.match_info["kind"]
    name = request.match_info["name"]
    directory = TRAINING_REPORTS_DIR if kind == "training" else BACKTEST_REPORTS_DIR
    path = directory / name
    if not path.exists():
        return _json_response({"error": "Report not found"}, status=404)

    payload = _read_json(path)
    trades = []
    trades_csv = payload.get("trades_csv")
    if trades_csv:
        trades_path = Path(trades_csv)
        if not trades_path.is_absolute():
            trades_path = Path.cwd() / trades_csv
        if trades_path.exists():
            trades = _read_csv(trades_path)

    return _json_response(
        {
            "name": name,
            "kind": kind,
            "payload": payload,
            "trades": trades,
        }
    )


def _append_job_log(job: Dict[str, Any], message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    job.setdefault("logs", []).append(f"[{timestamp}] {message}")
    job["logs"] = job["logs"][-MAX_LOG_LINES:]
    job["updated_at"] = datetime.now().isoformat()


async def _run_job(job_id: str, action: str, params: Dict[str, Any], jobs: Dict[str, Dict[str, Any]]) -> None:
    job = jobs[job_id]
    job["status"] = "running"
    job["updated_at"] = datetime.now().isoformat()

    def emit(message: str) -> None:
        _append_job_log(job, str(message))

    try:
        config = load_config()
        symbol = params.get("symbol", "BTC/USDT:USDT")
        config.symbols = [symbol]
        config.data.historical_days = int(params.get("days", 7))
        config.mode = TradingMode.BACKTEST

        if action == "train":
            result = await _run_training(config, symbol, params.get("period", "30d"), emit=emit)
        elif action == "backtest":
            result = await _run_backtest(config, params.get("strategy", "ai"), emit=emit)
        elif action == "research":
            result = await _run_research(
                config,
                symbol,
                params.get("period", "30d"),
                int(params.get("days", 7)),
                params.get("strategy", "ai"),
                emit=emit,
            )
        else:
            raise ValueError(f"Unsupported action: {action}")

        job["status"] = "completed"
        job["result"] = result
        job["overview"] = _overview_payload()
        _append_job_log(job, "Workflow completed.")
    except Exception as exc:
        job["status"] = "failed"
        job["error"] = str(exc)
        _append_job_log(job, f"Workflow failed: {exc}")
    finally:
        job["updated_at"] = datetime.now().isoformat()


async def _handle_run(request: web.Request) -> web.Response:
    app = request.app
    jobs: Dict[str, Dict[str, Any]] = app["jobs"]
    payload = await request.json()
    action = payload.get("action", "research")
    job_id = str(uuid.uuid4())[:8]
    job = {
        "id": job_id,
        "action": action,
        "params": payload,
        "status": "queued",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "logs": [],
    }
    jobs[job_id] = job
    app["tasks"][job_id] = asyncio.create_task(_run_job(job_id, action, payload, jobs))
    return _json_response({"job_id": job_id, "status": "queued"})


async def _handle_jobs(request: web.Request) -> web.Response:
    jobs = list(request.app["jobs"].values())
    jobs.sort(key=lambda item: item["created_at"], reverse=True)
    return _json_response({"jobs": jobs[:10]})


async def _handle_job(request: web.Request) -> web.Response:
    job = request.app["jobs"].get(request.match_info["job_id"])
    if not job:
        return _json_response({"error": "Job not found"}, status=404)
    return _json_response(job)


async def _run_trading_session(session: Dict[str, Any]) -> None:
    engine: TradingEngine = session["engine"]
    try:
        await engine.run()
    except Exception as exc:
        _append_job_log(session, f"Trading engine failed: {exc}")
        session["error"] = str(exc)
    finally:
        session["task"] = None


async def _handle_trading_status(request: web.Request) -> web.Response:
    return _json_response(_trading_status_payload(request.app["trading"]))


async def _handle_trading_start(request: web.Request) -> web.Response:
    app = request.app
    session = app["trading"]
    payload = await request.json()

    if session.get("task") and not session["task"].done():
        return _json_response({"error": "Trading engine already running"}, status=409)

    mode = payload.get("mode", "paper")
    symbol = payload.get("symbol", "BTC/USDT:USDT")
    if mode == "live" and not payload.get("confirm_live"):
        return _json_response({"error": "Live trading requires explicit confirmation"}, status=400)

    config = load_config()
    config.symbols = [symbol]
    config.exchange.leverage = int(payload.get("leverage", config.exchange.leverage))
    config.data.update_interval = int(payload.get("interval", config.data.update_interval))
    config.strategy.confidence_threshold = float(payload.get("confidence", config.strategy.confidence_threshold))
    config.risk.stop_loss_pct = float(payload.get("stop_loss_pct", config.risk.stop_loss_pct))
    config.risk.take_profit_pct = float(payload.get("take_profit_pct", config.risk.take_profit_pct))

    if mode == "paper":
        config.mode = TradingMode.PAPER_TRADING
        config.trading_mode = MarketMode.TESTNET
        config.apply_market_mode()
        exchange = PaperExchange(
            initial_balance={"USDT": float(payload.get("balance", 10000.0))},
            default_leverage=config.exchange.leverage,
            use_api_balance=False,
        )
    else:
        config.mode = TradingMode.LIVE_TRADING
        config.trading_mode = MarketMode.LIVE
        config.apply_market_mode()
        exchange = create_exchange_from_config()

    set_config(config)
    data_feed = create_data_feed_from_config()
    market_data = MarketData(data_feed)
    strategy = AIStrategy()
    risk_manager = RiskManager()
    engine = TradingEngine(
        config=config,
        strategy=strategy,
        exchange=exchange,
        market_data=market_data,
        risk_manager=risk_manager,
        persist_state=(mode == "live"),
    )

    session.update(
        {
            "mode": mode,
            "symbol": symbol,
            "engine": engine,
            "started_at": datetime.now().isoformat(),
            "logs": [],
            "error": None,
        }
    )
    _append_job_log(session, f"Starting {mode} AI auto trading for {symbol}")
    session["task"] = asyncio.create_task(_run_trading_session(session))

    return _json_response(_trading_status_payload(session))


async def _handle_trading_stop(request: web.Request) -> web.Response:
    session = request.app["trading"]
    task = session.get("task")
    engine = session.get("engine")

    if not task or task.done() or not engine:
        return _json_response({"running": False, "logs": session.get("logs", [])})

    engine.stop()
    _append_job_log(session, "Stop signal sent to trading engine")
    try:
        await asyncio.wait_for(task, timeout=5)
    except asyncio.TimeoutError:
        task.cancel()
        _append_job_log(session, "Trading engine task cancelled after timeout")
    except Exception as exc:
        _append_job_log(session, f"Trading engine stop error: {exc}")
    finally:
        session["task"] = None

    return _json_response(_trading_status_payload(session))


def create_app() -> web.Application:
    app = web.Application()
    app["jobs"] = {}
    app["tasks"] = {}
    app["trading"] = {"logs": [], "task": None, "engine": None, "mode": "paper", "symbol": "BTC/USDT:USDT"}

    app.router.add_get("/", _handle_index)
    app.router.add_static("/static/", WEB_ROOT)
    app.router.add_get("/api/overview", _handle_overview)
    app.router.add_get("/api/reports/{kind}/{name}", _handle_report)
    app.router.add_post("/api/run", _handle_run)
    app.router.add_get("/api/jobs", _handle_jobs)
    app.router.add_get("/api/jobs/{job_id}", _handle_job)
    app.router.add_get("/api/trading/status", _handle_trading_status)
    app.router.add_post("/api/trading/start", _handle_trading_start)
    app.router.add_post("/api/trading/stop", _handle_trading_stop)
    return app


def main() -> None:
    app = create_app()
    web.run_app(app, host="127.0.0.1", port=8080)


if __name__ == "__main__":
    main()
