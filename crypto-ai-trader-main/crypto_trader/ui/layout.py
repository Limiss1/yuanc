from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.layout import Dimension
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.widgets import Box, Button, SearchToolbar

from .custom_widgets import CustomTextArea

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

MAXIMUM_OUTPUT_PANE_LINE_COUNT = 5000
MAXIMUM_LOG_PANE_LINE_COUNT = 5000


def create_input_field(completer: Completer = None):
    return CustomTextArea(
        height=10,
        prompt='>>> ',
        style='class:input_field',
        multiline=False,
        focus_on_click=True,
        auto_suggest=AutoSuggestFromHistory(),
        completer=completer,
        complete_while_typing=True,
        history=InMemoryHistory(),
    )


def create_output_field():
    return CustomTextArea(
        style='class:output_field',
        focus_on_click=False,
        read_only=False,
        scrollbar=True,
        max_line_count=MAXIMUM_OUTPUT_PANE_LINE_COUNT,
        initial_text=HEADER,
    )


def create_timer():
    return CustomTextArea(
        style='class:footer',
        focus_on_click=False,
        read_only=False,
        scrollbar=False,
        max_line_count=1,
        width=30,
    )


def create_process_monitor():
    return CustomTextArea(
        style='class:footer',
        focus_on_click=False,
        read_only=False,
        scrollbar=False,
        max_line_count=1,
        align=WindowAlign.RIGHT,
    )


def create_trade_monitor():
    return CustomTextArea(
        style='class:footer',
        focus_on_click=False,
        read_only=False,
        scrollbar=False,
        max_line_count=1,
    )


def create_search_field() -> SearchToolbar:
    return SearchToolbar(
        text_if_not_searching=[('class:primary', "[CTRL + F] to start searching.")],
        forward_search_prompt=[('class:primary', "Search logs [Press CTRL + F to hide search] >>> ")],
        ignore_case=True,
    )


def create_log_field(search_field: SearchToolbar):
    return CustomTextArea(
        style='class:log_field',
        text="Running Logs\n",
        focus_on_click=False,
        read_only=False,
        scrollbar=True,
        max_line_count=MAXIMUM_LOG_PANE_LINE_COUNT,
        initial_text="Running Logs \n",
        search_field=search_field,
        preview_search=False,
    )


def create_live_field():
    return CustomTextArea(
        style='class:log_field',
        focus_on_click=False,
        read_only=False,
        scrollbar=True,
        max_line_count=MAXIMUM_OUTPUT_PANE_LINE_COUNT,
    )


def create_log_toggle(function):
    return Button(
        text='> Ctrl+T',
        width=10,
        handler=function,
        left_symbol='',
        right_symbol='',
    )


def create_tab_button(text, function, margin=2, left_symbol=' ', right_symbol=' '):
    return Button(
        text=text,
        width=len(text) + margin,
        handler=function,
        left_symbol=left_symbol,
        right_symbol=right_symbol,
    )


def generate_layout(
    input_field,
    output_field,
    log_field,
    right_pane_toggle,
    log_field_button,
    search_field,
    timer,
    process_monitor,
    trade_monitor,
    command_tabs,
    get_version,
    get_strategy,
    get_mode,
    get_status,
):
    components = {}

    components["item_top_version"] = Window(FormattedTextControl(get_version), style="class:header")
    components["item_top_strategy"] = Window(FormattedTextControl(get_strategy), style="class:header")
    components["item_top_mode"] = Window(FormattedTextControl(get_mode), style="class:header")
    components["item_top_status"] = Window(FormattedTextControl(get_status), style="class:header")
    components["item_top_toggle"] = right_pane_toggle
    components["pane_top"] = VSplit([
        components["item_top_version"],
        components["item_top_strategy"],
        components["item_top_mode"],
        components["item_top_status"],
        components["item_top_toggle"],
    ], height=1)

    components["pane_bottom"] = VSplit([
        trade_monitor,
        process_monitor,
        timer,
    ], height=1)

    output_pane = Box(body=output_field, padding=0, padding_left=2, style="class:output_field")
    input_pane = Box(body=input_field, padding=0, padding_left=2, padding_top=1, style="class:input_field")
    components["pane_left"] = HSplit([output_pane, input_pane], width=Dimension(weight=1))

    if all(not t.is_selected for t in command_tabs.values()):
        log_field_button.window.style = "class:tab_button.focused"
    else:
        log_field_button.window.style = "class:tab_button"

    tab_buttons = [log_field_button]
    for tab in sorted(command_tabs.values(), key=lambda x: x.tab_index):
        if tab.button is not None:
            if tab.is_selected:
                tab.button.window.style = "class:tab_button.focused"
            else:
                tab.button.window.style = "class:tab_button"
            tab.close_button.window.style = tab.button.window.style
            tab_buttons.append(VSplit([tab.button, tab.close_button]))

    pane_right_field = log_field
    focused_right_field = [tab.output_field for tab in command_tabs.values() if tab.is_selected]
    if focused_right_field:
        pane_right_field = focused_right_field[0]

    components["pane_right_top"] = VSplit(
        tab_buttons, height=1, style="class:log_field", padding_char=" ", padding=2
    )

    components["pane_right"] = ConditionalContainer(
        Box(
            body=HSplit([components["pane_right_top"], pane_right_field, search_field], width=Dimension(weight=1)),
            padding=0, padding_left=2, style="class:log_field"
        ),
        filter=True
    )

    components["hint_menus"] = [
        Float(
            xcursor=True, ycursor=True, transparent=True,
            content=CompletionsMenu(max_height=16, scroll_offset=1)
        )
    ]

    root_container = HSplit([
        components["pane_top"],
        VSplit([
            FloatContainer(components["pane_left"], components["hint_menus"]),
            components["pane_right"],
        ]),
        components["pane_bottom"],
    ])

    return Layout(root_container, focused_element=input_field), components
