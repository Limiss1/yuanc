"""
Crypto AI Trader TUI - Hummingbot-Style Terminal Interface
Uses prompt_toolkit to replicate Hummingbot's exact UI layout and interaction.
"""

import sys
import os
import asyncio
import json
import hashlib
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Deque
from collections import deque
from decimal import Decimal

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition, has_focus, is_done, is_true, to_filter
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Dimension, Layout
from prompt_toolkit.layout.containers import (
    ConditionalContainer, Float, FloatContainer,
    HSplit, VSplit, Window, WindowAlign,
)
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.processors import (
    AppendAutoSuggestion, BeforeInput, ConditionalProcessor, PasswordProcessor,
)
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Box, Button, SearchToolbar, Dialog, Label as PtLabel, TextArea as PtTextArea
from prompt_toolkit.history import InMemoryHistory

import psutil

APP_PASSWORD_HASH = hashlib.sha256("crypto2024".encode()).hexdigest()
PASSWORD_FILE = PROJECT_ROOT / ".gui_auth"


def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def load_password_hash() -> str:
    if PASSWORD_FILE.exists():
        with open(PASSWORD_FILE, "r") as f:
            return f.read().strip()
    return APP_PASSWORD_HASH


HEADER = r"""
                                                    *,.
                                                    *,,,*
                                                ,,,,,,,               *
                                                ,,,,,,,,           ,,,,
                                                *,,,,,,,,(        .,,,,,,
                                            /,,,,,,,,,,     .*,,,,,,,,
                                            .,,,,,,,,,,,.  ,,,,,,,,,,,*
                                            ,,,,,,,,,,,,,,,,,,,,,,,,,,,
                                //      ,,,,,,,,,,,,,,,,,,,,,,,,,,,,#*%
                            .,,,,,,,,. *,,,,,,,,,,,,,,,,,,,,,,,,,,,%%%%%%&@
                            ,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,%%%%%%%&
                        ,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,%%%%%%%&
                        /*,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,(((((%%&
                    **.         #,,,,,,,,,,,,,,,,,,,,,,,,,,,,,((((((((((#.
                **               *,,,,,,,,,,,,,,,,,,,,,,,,**/(((((((((((((*
                                    ,,,,,,,,,,,,,,,,,,,,*********((((((((((((
                                    ,,,,,,,,,,,,,,,**************((((((((@
                                    (,,,,,,,,,,,,,,,***************(#
                                        *,,,,,,,,,,,,,,,,**************/
                                        ,,,,,,,,,,,,,,,***************/
                                            ,,,,,,,,,,,,,,****************
                                            .,,,,,,,,,,,,**************/
                                                ,,,,,,,,*******,
                                                *,,,,,,,,********
                                                ,,,,,,,,,/******/
                                                ,,,,,,,,,@  /****/
                                                ,,,,,,,,
                                                , */

  ██████╗██████╗ ██╗   ██╗██████╗ ████████╗ ██████╗ ██╗   ██╗███████╗██████╗
 ██╔════╝██╔══██╗╚██╗ ██╔╝██╔══██╗╚══██╔══╝██╔═══██╗██║   ██║██╔════╝██╔══██╗
 ██║     ██████╔╝ ╚████╔╝ ██████╔╝   ██║   ██║   ██║██║   ██║█████╗  ██████╔╝
 ██║     ██╔══██╗  ╚██╔╝  ██╔═══╝    ██║   ██║   ██║╚██╗ ██╔╝██╔══╝  ██╔══██╗
 ╚██████╗██║  ██║   ██║   ██║        ██║   ╚██████╔╝ ╚████╔╝ ███████╗██║  ██║
  ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚═╝        ╚═╝    ╚═════╝   ╚═══╝  ╚══════╝╚═╝  ╚═╝

======================================================================================
Crypto AI Trader - USDT Perpetual Futures AI-Powered Trading System

- AI Strategy: XGBoost 3-class prediction (BUY/HOLD/SELL)
- Exchange: Binance USDT-M Futures
- Risk: Auto stop-loss / take-profit with adaptive confidence

Useful Commands:
- setup       Interactive setup wizard (F2)
- start       Start trading engine (F5)
- stop        Stop trading engine (F6)
- status      Show trading status (F9)
- config      Show / modify configuration
- balance     Show account balance
- positions   Show open positions
- orders      Show open orders
- price       Show live prices
- predict     Run AI prediction
- retrain     Retrain AI model
- cleanup     Cancel all orders & close positions
- password    Change login password
- help        List all commands
- exit        Exit application

"""

UI_STYLE = {
    "output_field":               "bg:#171E2B #1CD085",
    "input_field":                "bg:#000000 #FFFFFF",
    "log_field":                  "bg:#171E2B #FFFFFF",
    "header":                     "bg:#000000 #AAAAAA",
    "footer":                     "bg:#000000 #AAAAAA",
    "search":                     "bg:#000000 #93C36D",
    "search.current":             "bg:#000000 #1CD085",
    "primary":                    "#1CD085",
    "warning":                    "#93C36D",
    "error":                      "#F5634A",
    "tab_button.focused":         "bg:#1CD085 #171E2B",
    "tab_button":                 "bg:#FFFFFF #000000",
    "dialog":                     "bg:#171E2B",
    "dialog frame.label":         "bg:#FFFFFF #000000",
    "dialog.body":                "bg:#000000 ",
    "dialog shadow":              "bg:#171E2B",
    "button":                     "bg:#FFFFFF #000000",
    "text-area":                  "bg:#000000 #FFFFFF",
    "primary_label":              "bg:#1CD085 #171E2B",
    "secondary_label":            "bg:#5E6673 #171E2B",
    "success_label":              "bg:#0ECB81 #171E2B",
    "warning_label":              "bg:#FCD535 #171E2B",
    "info_label":                 "bg:#1E80FF #171E2B",
    "error_label":                "bg:#F6465D #171E2B",
    "gold_label":                 "bg:#171E2B #FFD700",
    "silver_label":               "bg:#171E2B #C0C0C0",
    "bronze_label":               "bg:#171E2B #CD7F32",
}


class CustomBuffer(Buffer):
    def validate_and_handle(self):
        valid = self.validate(set_cursor=True)
        if valid:
            if self.accept_handler:
                keep_text = self.accept_handler(self)
            else:
                keep_text = False
            if not keep_text:
                self.reset()


class CustomTextArea:
    def __init__(self, text='', multiline=True, password=False,
                 lexer=None, auto_suggest=None, completer=None,
                 complete_while_typing=True, accept_handler=None, history=None,
                 focusable=True, focus_on_click=False, wrap_lines=True,
                 read_only=False, width=None, height=None,
                 dont_extend_height=False, dont_extend_width=False,
                 line_numbers=False, get_line_prefix=None, scrollbar=False,
                 style='', search_field=None, preview_search=True, prompt='',
                 input_processors=None, max_line_count=1000, initial_text="",
                 align=WindowAlign.LEFT):

        if search_field is None:
            search_control = None
        elif isinstance(search_field, SearchToolbar):
            search_control = search_field.control

        if input_processors is None:
            input_processors = []

        self.completer = completer
        self.complete_while_typing = complete_while_typing
        self.lexer = lexer
        self.auto_suggest = auto_suggest
        self.read_only = read_only
        self.wrap_lines = wrap_lines
        self.max_line_count = max_line_count

        self.buffer = CustomBuffer(
            document=Document(text, 0),
            multiline=multiline,
            read_only=Condition(lambda: is_true(self.read_only)),
            completer=completer,
            complete_while_typing=Condition(lambda: is_true(self.complete_while_typing)),
            auto_suggest=auto_suggest,
            accept_handler=accept_handler,
            history=history,
        )

        procs = [
            ConditionalProcessor(
                AppendAutoSuggestion(),
                has_focus(self.buffer) & ~is_done),
            ConditionalProcessor(
                processor=PasswordProcessor(),
                filter=to_filter(password)
            ),
            BeforeInput(prompt, style='class:text-area.prompt'),
        ] + input_processors

        self.control = BufferControl(
            buffer=self.buffer,
            lexer=lexer,
            input_processors=procs,
            search_buffer_control=search_control,
            preview_search=preview_search,
            focusable=focusable,
            focus_on_click=focus_on_click,
        )

        if multiline:
            right_margins = [ScrollbarMargin(display_arrows=True)] if scrollbar else []
            left_margins = []
        else:
            left_margins = []
            right_margins = []

        style = 'class:text-area ' + style

        self.window = Window(
            height=height,
            width=width,
            dont_extend_height=dont_extend_height,
            dont_extend_width=dont_extend_width,
            content=self.control,
            style=style,
            wrap_lines=Condition(lambda: is_true(self.wrap_lines)),
            left_margins=left_margins,
            right_margins=right_margins,
            get_line_prefix=get_line_prefix,
            align=align,
        )

        self.log_lines: Deque[str] = deque()
        self.log(initial_text)

    @property
    def text(self):
        return self.buffer.text

    @text.setter
    def text(self, value):
        self.buffer.set_document(Document(value, 0), bypass_readonly=True)

    @property
    def document(self):
        return self.buffer.document

    @document.setter
    def document(self, value):
        self.buffer.document = value

    def __pt_container__(self):
        return self.window

    def log(self, text: str, save_log: bool = True, silent: bool = False):
        if self.window.render_info is None:
            max_width = 120
        else:
            max_width = self.window.render_info.window_width - 2

        repls = (('<b>', ''), ('</b>', ''), ('<pre>', ''), ('</pre>', ''))
        for r in repls:
            text = text.replace(*r)

        new_lines_raw: List[str] = str(text).split('\n')
        new_lines = []
        for line in new_lines_raw:
            while len(line) > max_width:
                new_lines.append(line[0:max_width])
                line = line[max_width:]
            new_lines.append(line)

        if save_log:
            self.log_lines.extend(new_lines)
            while len(self.log_lines) > self.max_line_count:
                self.log_lines.popleft()
            new_text: str = "\n".join(self.log_lines)
        else:
            new_text: str = "\n".join(new_lines)
        if not silent:
            self.buffer.document = Document(text=new_text, cursor_position=len(new_text))


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
            elif len(parts) == 2 and text.endswith(' '):
                pass


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

    def _create_input_field(self):
        return CustomTextArea(
            height=10,
            prompt='>>> ',
            style='class:input_field',
            multiline=False,
            focus_on_click=True,
            auto_suggest=AutoSuggestFromHistory(),
            completer=CommandCompleter(),
            complete_while_typing=True,
            history=InMemoryHistory(),
        )

    def _create_output_field(self):
        return CustomTextArea(
            style='class:output_field',
            focus_on_click=False,
            read_only=False,
            scrollbar=True,
            max_line_count=5000,
            initial_text=HEADER,
        )

    def _create_log_field(self, search_field):
        return CustomTextArea(
            style='class:log_field',
            text="Running Logs\n",
            focus_on_click=False,
            read_only=False,
            scrollbar=True,
            max_line_count=5000,
            initial_text="Running Logs \n",
            search_field=search_field,
            preview_search=False,
        )

    def _create_timer(self):
        return CustomTextArea(
            style='class:footer',
            focus_on_click=False,
            read_only=False,
            scrollbar=False,
            max_line_count=1,
            width=30,
        )

    def _create_process_monitor(self):
        return CustomTextArea(
            style='class:footer',
            focus_on_click=False,
            read_only=False,
            scrollbar=False,
            max_line_count=1,
            align=WindowAlign.RIGHT,
        )

    def _create_trade_monitor(self):
        return CustomTextArea(
            style='class:footer',
            focus_on_click=False,
            read_only=False,
            scrollbar=False,
            max_line_count=1,
        )

    def _create_search_field(self):
        return SearchToolbar(
            text_if_not_searching=[('class:primary', "[CTRL + F] to start searching.")],
            forward_search_prompt=[('class:primary', "Search logs [Press CTRL + F to hide search] >>> ")],
            ignore_case=True,
        )

    def _create_live_field(self):
        return CustomTextArea(
            style='class:log_field',
            focus_on_click=False,
            read_only=False,
            scrollbar=True,
            max_line_count=5000,
        )

    def _get_version(self):
        return [("class:header", "Crypto AI Trader v1.0")]

    def _get_strategy(self):
        if self._engine_running:
            return [("class:log_field", f"Strategy: AI (XGBoost)")]
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

    def _generate_layout(self):
        self.search_field = self._create_search_field()
        self.input_field = self._create_input_field()
        self.output_field = self._create_output_field()
        self.log_field = self._create_log_field(self.search_field)
        self.timer = self._create_timer()
        self.process_monitor = self._create_process_monitor()
        self.trade_monitor = self._create_trade_monitor()
        self.right_pane_toggle = Button(
            text='> Ctrl+T',
            width=10,
            handler=self._toggle_right_pane,
            left_symbol='',
            right_symbol='',
        )

        self.tab_logs_btn = Button(
            text=' logs ',
            width=8,
            handler=lambda: self._switch_tab("logs"),
            left_symbol=' ',
            right_symbol=' ',
        )
        self.tab_logs_btn.window.style = "class:tab_button.focused"

        self.tab_price_btn = Button(
            text=' price ',
            width=9,
            handler=lambda: self._switch_tab("price"),
            left_symbol=' ',
            right_symbol=' ',
        )
        self.tab_price_btn.window.style = "class:tab_button"

        self.tab_positions_btn = Button(
            text=' positions ',
            width=12,
            handler=lambda: self._switch_tab("positions"),
            left_symbol=' ',
            right_symbol=' ',
        )
        self.tab_positions_btn.window.style = "class:tab_button"

        self.tab_ai_btn = Button(
            text=' ai ',
            width=6,
            handler=lambda: self._switch_tab("ai"),
            left_symbol=' ',
            right_symbol=' ',
        )
        self.tab_ai_btn.window.style = "class:tab_button"

        self.price_field = self._create_live_field()
        self.positions_field = self._create_live_field()
        self.ai_field = self._create_live_field()

        item_top_version = Window(FormattedTextControl(self._get_version), style="class:header")
        item_top_strategy = Window(FormattedTextControl(self._get_strategy), style="class:header")
        item_top_mode = Window(FormattedTextControl(self._get_mode), style="class:header")
        item_top_status = Window(FormattedTextControl(self._get_status), style="class:header")
        item_top_toggle = self.right_pane_toggle

        pane_top = VSplit([
            item_top_version,
            item_top_strategy,
            item_top_mode,
            item_top_status,
            item_top_toggle,
        ], height=1)

        pane_bottom = VSplit([
            self.trade_monitor,
            self.process_monitor,
            self.timer,
        ], height=1)

        output_pane = Box(body=self.output_field, padding=0, padding_left=2, style="class:output_field")
        input_pane = Box(body=self.input_field, padding=0, padding_left=2, padding_top=1, style="class:input_field")
        pane_left = HSplit([output_pane, input_pane], width=Dimension(weight=1))

        tab_buttons = [
            self.tab_logs_btn,
            self.tab_price_btn,
            self.tab_positions_btn,
            self.tab_ai_btn,
        ]
        pane_right_top = VSplit(
            tab_buttons, height=1, style="class:log_field", padding_char=" ", padding=2
        )

        right_content = self._get_right_pane_content()

        pane_right = ConditionalContainer(
            Box(
                body=HSplit([pane_right_top, right_content, self.search_field], width=Dimension(weight=1)),
                padding=0, padding_left=2, style="class:log_field"
            ),
            filter=Condition(lambda: self._right_pane_visible)
        )

        hint_menus = [Float(
            xcursor=True, ycursor=True, transparent=True,
            content=CompletionsMenu(max_height=16, scroll_offset=1)
        )]

        root_container = HSplit([
            pane_top,
            VSplit([
                FloatContainer(pane_left, hint_menus),
                pane_right,
            ]),
            pane_bottom,
        ])

        return Layout(root_container, focused_element=self.input_field)

    def _get_right_pane_content(self):
        if self._current_tab == "logs":
            return self.log_field
        elif self._current_tab == "price":
            return self.price_field
        elif self._current_tab == "positions":
            return self.positions_field
        elif self._current_tab == "ai":
            return self.ai_field
        return self.log_field

    def _switch_tab(self, tab_name):
        self._current_tab = tab_name
        for name, btn in [
            ("logs", self.tab_logs_btn),
            ("price", self.tab_price_btn),
            ("positions", self.tab_positions_btn),
            ("ai", self.tab_ai_btn),
        ]:
            if name == tab_name:
                btn.window.style = "class:tab_button.focused"
            else:
                btn.window.style = "class:tab_button"

        self._rebuild_layout()

    def _toggle_right_pane(self):
        self._right_pane_visible = not self._right_pane_visible
        if self._right_pane_visible:
            self.right_pane_toggle.text = '> Ctrl+T'
        else:
            self.right_pane_toggle.text = '< Ctrl+T'

    def _rebuild_layout(self):
        self.layout = self._generate_layout()
        self.app.layout = self.layout
        self.app.invalidate()

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

    def _log(self, text: str, save_log: bool = True):
        if self._engine_running:
            self.output_field.log(text, save_log=save_log)
        else:
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

        if cmd == "help":
            self._cmd_help()
        elif cmd == "setup":
            self._cmd_setup()
        elif cmd == "start":
            self._cmd_start(args)
        elif cmd == "stop":
            self._cmd_stop()
        elif cmd == "status":
            self._cmd_status()
        elif cmd == "config":
            self._cmd_config(args)
        elif cmd == "balance":
            self._cmd_balance()
        elif cmd == "positions":
            self._cmd_positions()
        elif cmd == "orders":
            self._cmd_orders()
        elif cmd == "price":
            self._cmd_price(args)
        elif cmd == "predict":
            self._cmd_predict()
        elif cmd == "retrain":
            self._cmd_retrain()
        elif cmd == "cleanup":
            self._cmd_cleanup()
        elif cmd == "password":
            self._cmd_password(args)
        elif cmd == "exit" or cmd == "quit":
            self._cmd_exit()
        else:
            self._log(f"Unknown command: {cmd}. Type 'help' for available commands.")

    async def _prompt(self, prompt_text: str, default: str = "", is_password: bool = False) -> str:
        self._change_prompt(prompt_text, is_password=is_password)
        self.app.invalidate()
        self._pending_prompt = None
        self._prompt_event = asyncio.Event()
        await self._prompt_event.wait()
        result = self._pending_prompt
        self._pending_prompt = None
        self._prompt_event = None
        self._change_prompt(">>> ", is_password=False)
        self.app.invalidate()
        if result is None or result.strip() == "":
            return default
        return result.strip()

    def _change_prompt(self, prompt: str, is_password: bool = False):
        self.input_field.buffer.document = Document("", 0)
        procs = []
        if is_password:
            procs.append(PasswordProcessor())
        procs.append(BeforeInput(prompt, style='class:text-area.prompt'))
        self.input_field.control.input_processors = procs

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

        api_key = await self._prompt("API Key: ", default=self.config_values["api_key"], is_password=True)
        if api_key:
            self.config_values["api_key"] = api_key
        self._log("  API Key: ******")

        api_secret = await self._prompt("API Secret: ", default=self.config_values["api_secret"], is_password=True)
        if api_secret:
            self.config_values["api_secret"] = api_secret
        self._log("  API Secret: ******")

        symbol = await self._prompt(f"Symbol [BTC/USDT:USDT]: ", default=self.config_values["symbol"])
        if symbol:
            self.config_values["symbol"] = symbol
        self._log(f"  Symbol: {self.config_values['symbol']}")

        leverage = await self._prompt(f"Leverage (1-125) [{self.config_values['leverage']}]: ", default=str(self.config_values["leverage"]))
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

        conf = await self._prompt(f"Confidence Threshold [{self.config_values['confidence']}]: ", default=str(self.config_values["confidence"]))
        try:
            self.config_values["confidence"] = float(conf)
        except ValueError:
            pass
        self._log(f"  Confidence: {self.config_values['confidence']:.0%}")

        interval = await self._prompt(f"Update Interval (s) [{self.config_values['interval']}]: ", default=str(self.config_values["interval"]))
        try:
            self.config_values["interval"] = int(interval)
        except ValueError:
            pass
        self._log(f"  Interval: {self.config_values['interval']}s")

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
        self.app.exit()

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

        try:
            trade_monitor_text = (
                f"Trades: {self._trade_count}, "
                f"Total P&L: {self._total_pnl:+.2f} USDT, "
                f"Return %: {self._return_pct:+.2%}"
            )
            self.trade_monitor.log(trade_monitor_text, save_log=False)
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

    async def _timer_loop(self):
        count = 1
        while True:
            count += 1
            mins, sec = divmod(count, 60)
            hour, mins = divmod(mins, 60)
            days, hour = divmod(hour, 24)
            self.timer.log(f"Uptime: {days:>3} day(s), {hour:02}:{mins:02}:{sec:02}", save_log=False)
            await asyncio.sleep(1)

    async def _process_monitor_loop(self):
        process = psutil.Process()
        while True:
            try:
                with process.oneshot():
                    threads = process.num_threads()
                    cpu = process.cpu_percent()
                    mem = process.memory_info()
                    self.process_monitor.log(
                        f"CPU: {cpu:>5}%, Mem: {mem.rss / 1024 / 1024:.0f}MB, Threads: {threads}",
                        save_log=False,
                    )
            except Exception:
                pass
            await asyncio.sleep(1)

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

    def run(self):
        self._authenticate()

        self.layout = self._generate_layout()

        bindings = KeyBindings()

        @bindings.add('c-t')
        def _(event):
            self._toggle_right_pane()

        @bindings.add('f2')
        def _(event):
            self._cmd_setup()

        @bindings.add('f5')
        def _(event):
            self._handle_input("start")

        @bindings.add('f6')
        def _(event):
            self._handle_input("stop")

        @bindings.add('f9')
        def _(event):
            self._handle_input("status")

        self.input_field.buffer.accept_handler = lambda buff: self._accept_input(buff)

        self.app = Application(
            layout=self.layout,
            full_screen=True,
            key_bindings=bindings,
            style=Style.from_dict(UI_STYLE),
            mouse_support=True,
            clipboard=PyperclipClipboard(),
        )

        loop = asyncio.get_event_loop()
        loop.create_task(self._timer_loop())
        loop.create_task(self._process_monitor_loop())

        loop.run_until_complete(self.app.run_async())

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


def save_password(pw: str):
    with open(PASSWORD_FILE, "w") as f:
        f.write(hash_password(pw))


if __name__ == "__main__":
    app = CryptoTraderApp()
    app.run()
