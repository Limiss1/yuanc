"""
Crypto AI Trader TUI - Hummingbot-Style Terminal Interface
Uses crypto_trader.ui package (adapted from Hummingbot) for UI components.
"""

import sys
import os
import asyncio
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from prompt_toolkit import Application
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import InMemoryHistory

from crypto_trader.ui import (
    CustomTextArea,
    create_input_field,
    create_output_field,
    create_timer,
    create_process_monitor,
    create_trade_monitor,
    create_search_field,
    create_log_field,
    create_live_field,
    create_log_toggle,
    create_tab_button,
    generate_layout,
    load_style,
    load_key_bindings,
    start_timer,
    start_process_monitor,
    start_trade_monitor,
)
from crypto_trader.ui.tab import CommandTab

APP_PASSWORD_HASH = hashlib.sha256("crypto2024".encode()).hexdigest()
PASSWORD_FILE = PROJECT_ROOT / ".gui_auth"


def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def load_password_hash() -> str:
    if PASSWORD_FILE.exists():
        with open(PASSWORD_FILE, "r") as f:
            return f.read().strip()
    return APP_PASSWORD_HASH


def save_password(pw: str):
    with open(PASSWORD_FILE, "w") as f:
        f.write(hash_password(pw))


class CommandCompleter(Completer):
    COMMANDS = [
        "start", "stop", "status", "config", "balance", "positions",
        "orders", "price", "predict", "retrain", "cleanup", "password",
        "setup", "help", "exit",
    ]

    COMMAND_ARGS = {
        "start": ["paper", "live"],
        "config": ["mode", "symbol", "leverage", "sl", "tp", "confidence", "api_key", "api_secret", "interval"],
        "price": ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"],
        "setup": [],
    }

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        parts = text.split()

        if len(parts) <= 1 and not text.endswith(' '):
            for cmd in self.COMMANDS:
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text))
        elif len(parts) >= 1 and parts[0] in self.COMMAND_ARGS:
            if len(parts) == 1 and text.endswith(' '):
                for arg in self.COMMAND_ARGS[parts[0]]:
                    yield Completion(arg, start_position=0)
            elif len(parts) == 2 and not text.endswith(' '):
                for arg in self.COMMAND_ARGS[parts[0]]:
                    if arg.startswith(parts[1]):
                        yield Completion(arg, start_position=-len(parts[1]))


class CryptoTraderApp:
    def __init__(self):
        self.engine = None
        self.config = None
        self.market_data = None
        self.data_feed = None
        self.exchange = None
        self.strategy = None
        self.risk_manager = None
        self._engine_running = False
        self._last_signals: Dict[str, Dict] = {}
        self._authenticated = False
        self._right_pane_visible = True
        self._current_tab = "logs"

        self.config_values = {
            "mode": "paper",
            "trading_mode": "testnet",
            "api_key": "",
            "api_secret": "",
            "symbol": "BTC/USDT:USDT",
            "leverage": 10,
            "stop_loss_pct": 0.15,
            "take_profit_pct": 0.30,
            "confidence": 0.60,
            "interval": 60,
        }

        self._load_env_config()

        self._trade_count = 0
        self._total_pnl = 0.0
        self._return_pct = 0.0
        self._win_count = 0
        self._loss_count = 0
        self._win_rate = 0.0
        self._start_time = time.time()
        self._pending_prompt = None
        self._prompt_event = None

        self.command_tabs: Dict[str, CommandTab] = {
            "price": CommandTab(name="price", tab_index=1),
            "positions": CommandTab(name="positions", tab_index=2),
            "ai": CommandTab(name="ai", tab_index=3),
        }

        self.app: Optional[Application] = None
        self.layout = None
        self.layout_components = None

    def _load_env_config(self):
        try:
            env_path = PROJECT_ROOT / ".env"
            if env_path.exists():
                from dotenv import dotenv_values
                vals = dotenv_values(env_path)
                if vals.get("EXCHANGE_API_KEY"):
                    self.config_values["api_key"] = vals["EXCHANGE_API_KEY"]
                if vals.get("EXCHANGE_API_SECRET"):
                    self.config_values["api_secret"] = vals["EXCHANGE_API_SECRET"]
        except Exception:
            pass

        try:
            config_path = PROJECT_ROOT / "config" / "config.yaml"
            if config_path.exists():
                import yaml
                with open(config_path, "r") as f:
                    data = yaml.safe_load(f)
                if data.get("mode"):
                    self.config_values["mode"] = data["mode"]
                if data.get("trading_mode"):
                    self.config_values["trading_mode"] = data["trading_mode"]
                if data.get("symbols"):
                    self.config_values["symbol"] = data["symbols"][0]
                ex = data.get("exchange", {})
                if ex.get("leverage"):
                    self.config_values["leverage"] = ex["leverage"]
                risk = data.get("risk", {})
                if risk.get("stop_loss_pct"):
                    self.config_values["stop_loss_pct"] = risk["stop_loss_pct"] * 100
                if risk.get("take_profit_pct"):
                    self.config_values["take_profit_pct"] = risk["take_profit_pct"] * 100
                strat = data.get("strategy", {})
                if strat.get("confidence_threshold"):
                    self.config_values["confidence"] = strat["confidence_threshold"]
                dat = data.get("data", {})
                if dat.get("update_interval"):
                    self.config_values["interval"] = dat["update_interval"]
        except Exception:
            pass

    def _get_version(self):
        return [("class:header", "Crypto AI Trader v1.0")]

    def _get_strategy(self):
        if self._engine_running:
            return [("class:log_field", "Strategy: AI (XGBoost)")]
        return [("class:log_field", "Strategy: --")]

    def _get_mode(self):
        mode = self.config_values["mode"].upper()
        trading = self.config_values["trading_mode"].upper()
        if self._engine_running:
            return [("class:log_field", f"Mode: {mode} | Market: {trading}")]
        return [("class:log_field", "Mode: --")]

    def _get_status(self):
        if self._engine_running:
            return [("class:log_field", "Status: \U0001f7e2 RUNNING")]
        return [("class:log_field", "Status: \U0001f534 STOPPED")]

    def _init_ui_components(self):
        self.search_field = create_search_field()
        self.input_field = create_input_field(completer=CommandCompleter())
        self.output_field = create_output_field()
        self.log_field = create_log_field(self.search_field)
        self.right_pane_toggle = create_log_toggle(self._toggle_right_pane)
        self.log_field_button = create_tab_button("logs", self._log_button_clicked)
        self.timer = create_timer()
        self.process_monitor = create_process_monitor()
        self.trade_monitor = create_trade_monitor()
        self.price_field = create_live_field()
        self.positions_field = create_live_field()
        self.ai_field = create_live_field()

        self.command_tabs["price"].button = create_tab_button("price", lambda: self._tab_button_clicked("price"))
        self.command_tabs["price"].close_button = create_tab_button("x", lambda: self._close_button_clicked("price"), 1, '', ' ')
        self.command_tabs["price"].output_field = self.price_field

        self.command_tabs["positions"].button = create_tab_button("positions", lambda: self._tab_button_clicked("positions"))
        self.command_tabs["positions"].close_button = create_tab_button("x", lambda: self._close_button_clicked("positions"), 1, '', ' ')
        self.command_tabs["positions"].output_field = self.positions_field

        self.command_tabs["ai"].button = create_tab_button("ai", lambda: self._tab_button_clicked("ai"))
        self.command_tabs["ai"].close_button = create_tab_button("x", lambda: self._close_button_clicked("ai"), 1, '', ' ')
        self.command_tabs["ai"].output_field = self.ai_field

    def _redraw_app(self):
        self.layout, self.layout_components = generate_layout(
            input_field=self.input_field,
            output_field=self.output_field,
            log_field=self.log_field,
            right_pane_toggle=self.right_pane_toggle,
            log_field_button=self.log_field_button,
            search_field=self.search_field,
            timer=self.timer,
            process_monitor=self.process_monitor,
            trade_monitor=self.trade_monitor,
            command_tabs=self.command_tabs,
            get_version=self._get_version,
            get_strategy=self._get_strategy,
            get_mode=self._get_mode,
            get_status=self._get_status,
        )
        if self.app is not None:
            self.app.layout = self.layout
            self.app.invalidate()

    def _toggle_right_pane(self):
        if self.layout_components["pane_right"].filter():
            self.layout_components["pane_right"].filter = lambda: False
            self.layout_components["item_top_toggle"].text = '< Ctrl+T'
        else:
            self.layout_components["pane_right"].filter = lambda: True
            self.layout_components["item_top_toggle"].text = '> Ctrl+T'

    def _log_button_clicked(self):
        for tab in self.command_tabs.values():
            tab.is_selected = False
        self._current_tab = "logs"
        self._redraw_app()

    def _tab_button_clicked(self, tab_name: str):
        for tab in self.command_tabs.values():
            tab.is_selected = False
        self.command_tabs[tab_name].is_selected = True
        self._current_tab = tab_name
        self._redraw_app()

    def _close_button_clicked(self, tab_name: str):
        self.command_tabs[tab_name].button = None
        self.command_tabs[tab_name].close_button = None
        self.command_tabs[tab_name].output_field = None
        self.command_tabs[tab_name].is_selected = False
        for tab in self.command_tabs.values():
            if tab.tab_index > self.command_tabs[tab_name].tab_index:
                tab.tab_index -= 1
        self.command_tabs[tab_name].tab_index = 0
        self._current_tab = "logs"
        self._redraw_app()

    def _tab_navigate_left(self):
        selected_tabs = [t for t in self.command_tabs.values() if t.is_selected]
        if not selected_tabs:
            return
        selected_tab = selected_tabs[0]
        if selected_tab.tab_index == 1:
            self._log_button_clicked()
        else:
            left_tab = [t for t in self.command_tabs.values() if t.tab_index == selected_tab.tab_index - 1]
            if left_tab:
                self._tab_button_clicked(left_tab[0].name)

    def _tab_navigate_right(self):
        current_tabs = [t for t in self.command_tabs.values() if t.tab_index > 0]
        if not current_tabs:
            return
        selected_tab = [t for t in current_tabs if t.is_selected]
        if selected_tab:
            right_tab = [t for t in current_tabs if t.tab_index == selected_tab[0].tab_index + 1]
        else:
            right_tab = [t for t in current_tabs if t.tab_index == 1]
        if right_tab:
            self._tab_button_clicked(right_tab[0].name)

    def _log(self, text: str, save_log: bool = True):
        self.output_field.log(text, save_log=save_log)

    def _log_right(self, text: str):
        self.log_field.log(text)

    def _handle_input(self, text: str):
        text = text.strip()
        if not text:
            return

        parts = text.split()
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        cmd_map = {
            "start": lambda: self._cmd_start(args),
            "stop": self._cmd_stop,
            "status": self._cmd_status,
            "config": lambda: self._cmd_config(args),
            "balance": self._cmd_balance,
            "positions": self._cmd_positions,
            "orders": self._cmd_orders,
            "price": lambda: self._cmd_price(args),
            "predict": self._cmd_predict,
            "retrain": self._cmd_retrain,
            "cleanup": self._cmd_cleanup,
            "password": lambda: self._cmd_password(args),
            "setup": self._cmd_setup,
            "help": self._cmd_help,
            "exit": self._cmd_exit,
        }

        handler = cmd_map.get(cmd)
        if handler:
            handler()
        else:
            self._log(f"Unknown command: {cmd}. Type 'help' for available commands.")

    async def _prompt(self, prompt_text: str, default: str = "") -> str:
        self._prompt_event = asyncio.Event()
        self.input_field.control.input_processors = [
            __import__('prompt_toolkit.layout.processors', fromlist=['BeforeInput']).BeforeInput(
                prompt_text, style='class:text-area.prompt'
            ),
        ]
        self.app.invalidate()
        await self._prompt_event.wait()

        result = self._pending_prompt or default
        self._pending_prompt = None
        self._prompt_event = None

        self.input_field.control.input_processors = [
            __import__('prompt_toolkit.layout.processors', fromlist=['BeforeInput']).BeforeInput(
                '>>> ', style='class:text-area.prompt'
            ),
        ]
        self.app.invalidate()
        return result

    def _cmd_setup(self):
        asyncio.ensure_future(self._setup_wizard())

    async def _setup_wizard(self):
        self._log("\n╔══════════════════════════════════════════════╗")
        self._log("║       Crypto AI Trader - Setup Wizard       ║")
        self._log("╚══════════════════════════════════════════════╝\n")

        mode = await self._prompt("Trading mode (paper/live) [paper]: ", default=self.config_values["mode"])
        if mode in ("paper", "live"):
            self.config_values["mode"] = mode
        self._log(f"  Mode: {self.config_values['mode']}")

        market = await self._prompt("Market (testnet/live) [testnet]: ", default=self.config_values["trading_mode"])
        if market in ("testnet", "live"):
            self.config_values["trading_mode"] = market
        self._log(f"  Market: {self.config_values['trading_mode']}")

        api_key = await self._prompt("API Key: ", default=self.config_values["api_key"])
        if api_key:
            self.config_values["api_key"] = api_key
        self._log(f"  API Key: {'***' + api_key[-4:] if len(api_key) > 4 else '***'}")

        api_secret = await self._prompt("API Secret: ", default=self.config_values["api_secret"])
        if api_secret:
            self.config_values["api_secret"] = api_secret
        self._log(f"  API Secret: ***")

        symbol = await self._prompt("Symbol [BTC/USDT:USDT]: ", default=self.config_values["symbol"])
        if symbol:
            self.config_values["symbol"] = symbol
        self._log(f"  Symbol: {self.config_values['symbol']}")

        leverage = await self._prompt(f"Leverage [{self.config_values['leverage']}]: ", default=str(self.config_values["leverage"]))
        try:
            self.config_values["leverage"] = int(leverage)
        except ValueError:
            pass
        self._log(f"  Leverage: {self.config_values['leverage']}x")

        sl = await self._prompt(f"Stop Loss % [{self.config_values['stop_loss_pct']}]: ", default=str(self.config_values["stop_loss_pct"]))
        try:
            self.config_values["stop_loss_pct"] = float(sl)
        except ValueError:
            pass
        self._log(f"  Stop Loss: {self.config_values['stop_loss_pct']}%")

        tp = await self._prompt(f"Take Profit % [{self.config_values['take_profit_pct']}]: ", default=str(self.config_values["take_profit_pct"]))
        try:
            self.config_values["take_profit_pct"] = float(tp)
        except ValueError:
            pass
        self._log(f"  Take Profit: {self.config_values['take_profit_pct']}%")

        conf = await self._prompt(f"Confidence threshold [{self.config_values['confidence']}]: ", default=str(self.config_values["confidence"]))
        try:
            self.config_values["confidence"] = float(conf)
        except ValueError:
            pass
        self._log(f"  Confidence: {self.config_values['confidence']:.0%}")

        self._log("\n╔══════════════════════════════════════════════╗")
        self._log("║          Setup Complete!                     ║")
        self._log("║  Type 'start' or press F5 to begin trading   ║")
        self._log("╚══════════════════════════════════════════════╝\n")

    def _cmd_help(self):
        help_text = """
Available Commands:
  setup                 Interactive setup wizard (configure all settings)
  start [paper|live]    Start trading engine (default: paper)
  stop                  Stop trading engine
  status                Show trading status & statistics
  config [key] [value]  Show or modify configuration
  balance               Show account balance
  positions             Show open positions
  orders                Show open orders
  price [symbol]        Show live prices
  predict               Run AI prediction on configured symbol
  retrain               Retrain AI model
  cleanup               Cancel all orders & close positions
  password <new_pw>     Change login password
  help                  Show this help message
  exit                  Exit application

Keyboard Shortcuts:
  Ctrl+T                Toggle right pane
  Ctrl+F                Search in logs
  Ctrl+B/N              Navigate tabs left/right
  F2                    Quick setup wizard
  F5                    Start trading
  F6                    Stop trading
  F9                    Show status
  Tab                   Auto-complete commands
  Up/Down               Command history
"""
        self._log(help_text)

    def _cmd_start(self, args):
        if self._engine_running:
            self._log("Trading engine is already running.")
            return

        if args and args[0] in ["paper", "live"]:
            self.config_values["mode"] = args[0]

        self._log("Initializing trading components...")
        try:
            config = self._build_config()
        except Exception as e:
            self._log(f"Configuration error: {e}")
            return

        try:
            if not self._init_components(config):
                self._log("Failed to initialize components.")
                return
        except Exception as e:
            self._log(f"Initialization error: {e}")
            return

        self._engine_running = True
        self._start_time = time.time()
        self._log(f"Trading engine started. Mode: {self.config_values['mode'].upper()}, "
                   f"Market: {self.config_values['trading_mode'].upper()}, "
                   f"Symbol: {self.config_values['symbol']}, "
                   f"Leverage: {self.config_values['leverage']}x")
        self._log_right(f"[{datetime.now().strftime('%H:%M:%S')}] Engine started")

        asyncio.ensure_future(self._run_engine_async())
        asyncio.ensure_future(self._update_loop())

    def _cmd_stop(self):
        if not self._engine_running:
            self._log("Trading engine is not running.")
            return
        if self.engine:
            self.engine.stop()
        self._engine_running = False
        self._log("Trading engine stopped.")
        self._log_right(f"[{datetime.now().strftime('%H:%M:%S')}] Engine stopped")

    def _cmd_status(self):
        if not self._engine_running:
            self._log("Trading engine is not running. Use 'start' to begin.")
            return

        status_lines = [
            f"  Mode:            {self.config_values['mode'].upper()}",
            f"  Market:          {self.config_values['trading_mode'].upper()}",
            f"  Symbol:          {self.config_values['symbol']}",
            f"  Leverage:        {self.config_values['leverage']}x",
            f"  Stop Loss:       {self.config_values['stop_loss_pct']}%",
            f"  Take Profit:     {self.config_values['take_profit_pct']}%",
            f"  Confidence:      {self.config_values['confidence']:.0%}",
            f"  Interval:        {self.config_values['interval']}s",
            "",
            f"  Trades:          {self._trade_count}",
            f"  Win/Loss:        {self._win_count}/{self._loss_count}",
            f"  Win Rate:        {self._win_rate:.1%}",
            f"  Total P&L:       {self._total_pnl:+.2f} USDT",
            f"  Return:          {self._return_pct:+.2%}",
        ]

        if self.engine:
            try:
                status = self.engine.get_status()
                portfolio = status.get("portfolio", {})
                equity = portfolio.get("equity", 0)
                status_lines.extend([
                    "",
                    f"  Equity:          {equity:.2f} USDT",
                    f"  Risk Level:      {status.get('risk_level', '--').upper()}",
                    f"  Drawdown:        {portfolio.get('max_drawdown', 0):.2%}",
                ])
            except Exception:
                pass

        self._log("\n".join(status_lines))

    def _cmd_config(self, args):
        if not args:
            lines = ["Current Configuration:"]
            for k, v in self.config_values.items():
                if k in ("api_key", "api_secret") and v:
                    display = v[:6] + "..." + v[-4:] if len(v) > 10 else "***"
                else:
                    display = v
                lines.append(f"  {k:<18} {display}")
            self._log("\n".join(lines))
            return

        key = args[0]
        if key not in self.config_values:
            self._log(f"Unknown config key: {key}")
            self._log(f"Available keys: {', '.join(self.config_values.keys())}")
            return

        if len(args) < 2:
            val = self.config_values[key]
            if key in ("api_key", "api_secret") and val:
                val = val[:6] + "..." + val[-4:] if len(val) > 10 else "***"
            self._log(f"  {key} = {val}")
            return

        value = " ".join(args[1:])
        try:
            if key in ("leverage", "interval"):
                self.config_values[key] = int(value)
            elif key in ("stop_loss_pct", "take_profit_pct", "confidence"):
                self.config_values[key] = float(value)
            else:
                self.config_values[key] = value
            self._log(f"  {key} = {self.config_values[key]}")
        except ValueError:
            self._log(f"Invalid value for {key}: {value}")

    def _cmd_balance(self):
        if not self._engine_running or not self.exchange:
            self._log("Trading engine is not running.")
            return

        async def _fetch():
            try:
                balance = await self.exchange.get_balance()
                self._log(f"  Available: {balance.get('free', {})}")
                self._log(f"  Used:      {balance.get('used', {})}")
                self._log(f"  Total:     {balance.get('total', {})}")
            except Exception as e:
                self._log(f"Error fetching balance: {e}")

        asyncio.ensure_future(_fetch())

    def _cmd_positions(self):
        if not self._engine_running or not self.exchange:
            self._log("Trading engine is not running.")
            return

        async def _fetch():
            try:
                positions = await self.exchange.get_positions()
                if not positions:
                    self._log("  No open positions.")
                    return
                lines = [f"  {'Symbol':<12} {'Side':<6} {'Size':<12} {'Entry':<12} {'PnL':<12} {'SL':<12} {'TP':<12}"]
                lines.append("  " + "─" * 76)
                for pos in positions:
                    short = pos.symbol.replace("/USDT:USDT", "")
                    side = "LONG" if pos.side.value == "buy" else "SHORT"
                    pnl = float(pos.unrealized_pnl)
                    sl = pos.metadata.get("stop_loss") if pos.metadata else None
                    tp = pos.metadata.get("take_profit") if pos.metadata else None
                    lines.append(
                        f"  {short:<12} {side:<6} {float(pos.amount):<12.5f} "
                        f"{float(pos.entry_price):<12,.2f} {pnl:<+12.2f} "
                        f"{float(sl):<12,.2f} {float(tp):<12,.2f}" if sl and tp else
                        f"  {short:<12} {side:<6} {float(pos.amount):<12.5f} "
                        f"{float(pos.entry_price):<12,.2f} {pnl:<+12.2f} --          --"
                    )
                self._log("\n".join(lines))
            except Exception as e:
                self._log(f"Error fetching positions: {e}")

        asyncio.ensure_future(_fetch())

    def _cmd_orders(self):
        if not self._engine_running or not self.exchange:
            self._log("Trading engine is not running.")
            return

        async def _fetch():
            try:
                orders = await self.exchange.get_open_orders()
                if not orders:
                    self._log("  No open orders.")
                    return
                lines = [f"  {'ID':<12} {'Symbol':<12} {'Side':<6} {'Type':<10} {'Price':<12}"]
                lines.append("  " + "─" * 52)
                for order in orders:
                    oid = order.order_id[:10]
                    short = order.symbol.replace("/USDT:USDT", "")
                    side = order.side.value.upper()
                    otype = order.order_type.value.upper()
                    price = f"{float(order.price):,.2f}" if order.price else "MARKET"
                    lines.append(f"  {oid:<12} {short:<12} {side:<6} {otype:<10} {price:<12}")
                self._log("\n".join(lines))
            except Exception as e:
                self._log(f"Error fetching orders: {e}")

        asyncio.ensure_future(_fetch())

    def _cmd_price(self, args):
        symbol = args[0] if args else self.config_values["symbol"]

        async def _fetch():
            try:
                if not self.data_feed:
                    self._log("Data feed not initialized. Start the engine first.")
                    return
                ticker = await self.data_feed.fetch_ticker(symbol)
                if ticker:
                    short = symbol.replace("/USDT:USDT", "")
                    last = ticker.get("last", 0)
                    change = ticker.get("percentage", 0) or 0
                    bid = ticker.get("bid", 0)
                    ask = ticker.get("ask", 0)
                    vol = ticker.get("quoteVolume", 0) or 0
                    chg_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
                    self._log(f"  {short}/USDT")
                    self._log(f"  Price:    {last:,.2f}")
                    self._log(f"  24h Chg:  {chg_str}")
                    self._log(f"  Bid:      {bid:,.2f}")
                    self._log(f"  Ask:      {ask:,.2f}")
                    self._log(f"  Volume:   {vol:,.0f} USDT")
                else:
                    self._log(f"  No data for {symbol}")
            except Exception as e:
                self._log(f"Error fetching price: {e}")

        asyncio.ensure_future(_fetch())

    def _cmd_predict(self):
        if not self._engine_running or not self.strategy:
            self._log("Trading engine is not running. Use 'start' first.")
            return

        async def _do():
            try:
                symbol = self.config_values["symbol"]
                self._log(f"Running AI prediction for {symbol}...")
                signal = await self.strategy.analyze(symbol, self.market_data)
                if signal:
                    direction = signal.direction.name if hasattr(signal.direction, 'name') else str(signal.direction)
                    conf = signal.confidence
                    price = signal.price
                    self._last_signals[symbol] = {"direction": direction, "confidence": conf, "price": price}

                    if direction == "BUY":
                        self._log(f"  Prediction: \U0001f7e2 BUY  | Confidence: {conf:.1%} | Price: {price:,.2f}")
                    elif direction == "SELL":
                        self._log(f"  Prediction: \U0001f534 SELL | Confidence: {conf:.1%} | Price: {price:,.2f}")
                    else:
                        self._log(f"  Prediction: \U0001f7e1 HOLD | Confidence: {conf:.1%} | Price: {price:,.2f}")
                else:
                    self._log("  No signal generated.")
            except Exception as e:
                self._log(f"Prediction error: {e}")

        asyncio.ensure_future(_do())

    def _cmd_retrain(self):
        if not self._engine_running or not self.strategy or not self.market_data:
            self._log("Trading engine is not running. Use 'start' first.")
            return

        self._log("Retraining AI model...")

        async def _do():
            try:
                await self.strategy.retrain_model(self.market_data, self.config.symbols)
                self._log("Model retraining completed.")
            except Exception as e:
                self._log(f"Retrain error: {e}")

        asyncio.ensure_future(_do())

    def _cmd_cleanup(self):
        if not self._engine_running or not self.exchange:
            self._log("Trading engine is not running.")
            return

        self._log("Cleaning up positions and orders...")

        async def _do():
            try:
                for symbol in self.config.symbols:
                    await self.exchange.cancel_all_orders(symbol)
                self._log("Cleanup completed.")
            except Exception as e:
                self._log(f"Cleanup error: {e}")

        asyncio.ensure_future(_do())

    def _cmd_password(self, args):
        if not args:
            self._log("Usage: password <new_password>")
            return
        new_pw = args[0]
        save_password(new_pw)
        self._log("Password updated successfully.")

    def _cmd_exit(self):
        if self._engine_running and self.engine:
            self.engine.stop()
        if self.app:
            self.app.exit()

    def _build_config(self):
        from crypto_trader.infra.config import (
            TradingConfig, ExchangeConfig, StrategyConfig,
            RiskConfig, DataConfig, TradingMode, MarketMode, ExchangeType
        )

        cv = self.config_values
        trading_mode = TradingMode.PAPER_TRADING if cv["mode"] == "paper" else TradingMode.LIVE_TRADING
        market_mode = MarketMode.TESTNET if cv["trading_mode"] == "testnet" else MarketMode.LIVE

        config = TradingConfig(
            mode=trading_mode,
            trading_mode=market_mode,
            symbols=[cv["symbol"]],
            base_currency="USDT",
            exchange=ExchangeConfig(
                name=ExchangeType.BINANCE,
                api_key=cv["api_key"] or None,
                api_secret=cv["api_secret"] or None,
                testnet=(market_mode == MarketMode.TESTNET),
                leverage=cv["leverage"],
            ),
            strategy=StrategyConfig(
                name="ai",
                confidence_threshold=cv["confidence"],
                max_position_size=0.1,
                lookback_period=500,
            ),
            risk=RiskConfig(
                max_drawdown=0.15,
                daily_loss_limit=0.05,
                max_open_positions=3,
                stop_loss_pct=cv["stop_loss_pct"] / 100.0,
                take_profit_pct=cv["take_profit_pct"] / 100.0,
            ),
            data=DataConfig(
                update_interval=cv["interval"],
            ),
        )
        config.apply_market_mode()
        return config

    def _init_components(self, config):
        from crypto_trader.data.market_data import MarketData, CCXTDataFeed
        from crypto_trader.execution.exchange import CCXTExchange
        from crypto_trader.execution.paper_exchange import PaperExchange
        from crypto_trader.strategy.ai_strategy import AIStrategy
        from crypto_trader.risk.risk_manager import RiskManager
        from crypto_trader.infra.config import set_config

        set_config(config)

        self.data_feed = CCXTDataFeed(
            exchange_id=config.exchange.name.value,
            api_key=config.exchange.api_key,
            api_secret=config.exchange.api_secret,
            testnet=config.exchange.testnet,
            demo_api=config.exchange.demo_api,
        )
        self.market_data = MarketData(self.data_feed)

        if config.mode.value == "paper":
            self.exchange = PaperExchange(
                default_leverage=config.exchange.leverage,
                use_api_balance=True,
            )
        else:
            self.exchange = CCXTExchange(
                exchange_id=config.exchange.name.value,
                api_key=config.exchange.api_key,
                api_secret=config.exchange.api_secret,
                testnet=config.exchange.testnet,
                leverage=config.exchange.leverage,
                demo_api=config.exchange.demo_api,
            )

        self.strategy = AIStrategy()
        self.risk_manager = RiskManager()
        self.config = config
        return True

    async def _run_engine_async(self):
        try:
            from crypto_trader.execution.trading_engine import TradingEngine
            self.engine = TradingEngine(
                config=self.config,
                strategy=self.strategy,
                exchange=self.exchange,
                market_data=self.market_data,
                risk_manager=self.risk_manager,
            )
            await self.engine.run()
        except Exception as e:
            self._log(f"Engine error: {e}")
            self._engine_running = False

    async def _update_loop(self):
        while self._engine_running:
            try:
                await asyncio.sleep(5)
                await self._update_monitors()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _update_monitors(self):
        if self.engine:
            try:
                status = self.engine.get_status()
                self._trade_count = status.get("trade_count", 0)
                self._win_count = status.get("win_count", 0)
                self._loss_count = status.get("loss_count", 0)
                self._win_rate = status.get("win_rate", 0)
                portfolio = status.get("portfolio", {})
                self._total_pnl = portfolio.get("total_pnl", 0)
                self._return_pct = portfolio.get("total_pnl_pct", 0)
            except Exception:
                pass

        if self._current_tab == "price" and self.data_feed:
            try:
                symbol = self.config_values["symbol"]
                ticker = await self.data_feed.fetch_ticker(symbol)
                if ticker:
                    short = symbol.replace("/USDT:USDT", "")
                    last = ticker.get("last", 0)
                    change = ticker.get("percentage", 0) or 0
                    bid = ticker.get("bid", 0)
                    ask = ticker.get("ask", 0)
                    chg_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
                    self.price_field.log(
                        f"[{datetime.now().strftime('%H:%M:%S')}] "
                        f"{short}/USDT  {last:,.2f}  24h: {chg_str}  "
                        f"Bid: {bid:,.2f}  Ask: {ask:,.2f}"
                    )
            except Exception:
                pass

        if self._current_tab == "ai" and self.strategy:
            try:
                if hasattr(self.strategy, 'ai_model') and self.strategy.ai_model.model is not None:
                    acc = self.strategy.ai_model.accuracy_history[-1] if self.strategy.ai_model.accuracy_history else 0
                    for symbol in (self.config.symbols if self.config else [self.config_values["symbol"]]):
                        short = symbol.replace("/USDT:USDT", "")
                        if symbol in self._last_signals:
                            sig = self._last_signals[symbol]
                            direction = sig.get("direction", "HOLD")
                            conf = sig.get("confidence", 0)
                            self.ai_field.log(
                                f"[{datetime.now().strftime('%H:%M:%S')}] "
                                f"{short}  Direction: {direction}  Confidence: {conf:.1%}  Model Acc: {acc:.1%}"
                            )
                        else:
                            self.ai_field.log(
                                f"[{datetime.now().strftime('%H:%M:%S')}] "
                                f"{short}  Waiting for signal...  Model Acc: {acc:.1%}"
                            )
            except Exception:
                pass

        if self._current_tab == "positions" and self.exchange:
            try:
                positions = await self.exchange.get_positions()
                if positions:
                    for pos in positions[:5]:
                        short = pos.symbol.replace("/USDT:USDT", "")
                        side = "LONG" if pos.side.value == "buy" else "SHORT"
                        pnl = float(pos.unrealized_pnl)
                        self.positions_field.log(
                            f"[{datetime.now().strftime('%H:%M:%S')}] "
                            f"{short} {side} Size:{float(pos.amount):.5f} "
                            f"Entry:{float(pos.entry_price):,.2f} "
                            f"Mark:{float(pos.current_price):,.2f} "
                            f"PnL:{pnl:+.2f}"
                        )
                else:
                    self.positions_field.log(
                        f"[{datetime.now().strftime('%H:%M:%S')}] No open positions"
                    )
            except Exception:
                pass

    def _authenticate(self):
        import getpass
        stored_hash = load_password_hash()
        attempts = 0
        while attempts < 3:
            try:
                pw = getpass.getpass("Password: ")
            except Exception:
                pw = input("Password: ")
            if hash_password(pw) == stored_hash:
                return True
            print("Incorrect password. Try again.")
            attempts += 1
        print("Too many failed attempts. Exiting.")
        sys.exit(1)

    def _accept_input(self, buff):
        text = self.input_field.text.strip()
        if self._prompt_event is not None:
            self._pending_prompt = text
            self._prompt_event.set()
            return False
        if text:
            self._log(f"\n>>>  {text}", save_log=False)
            self._handle_input(text)
        return False

    def run(self):
        self._authenticate()

        self._init_ui_components()

        self.layout, self.layout_components = generate_layout(
            input_field=self.input_field,
            output_field=self.output_field,
            log_field=self.log_field,
            right_pane_toggle=self.right_pane_toggle,
            log_field_button=self.log_field_button,
            search_field=self.search_field,
            timer=self.timer,
            process_monitor=self.process_monitor,
            trade_monitor=self.trade_monitor,
            command_tabs=self.command_tabs,
            get_version=self._get_version,
            get_strategy=self._get_strategy,
            get_mode=self._get_mode,
            get_status=self._get_status,
        )

        bindings = load_key_bindings(self)

        self.input_field.accept_handler = self._accept_input

        self.app = Application(
            layout=self.layout,
            full_screen=True,
            key_bindings=bindings,
            style=load_style(),
            mouse_support=True,
            clipboard=PyperclipClipboard(),
        )

        loop = asyncio.get_event_loop()
        loop.create_task(start_timer(self.timer))
        loop.create_task(start_process_monitor(self.process_monitor))
        loop.create_task(start_trade_monitor(self.trade_monitor, app=self))

        loop.run_until_complete(self.app.run_async())


if __name__ == "__main__":
    app = CryptoTraderApp()
    app.run()
