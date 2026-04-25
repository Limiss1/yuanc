from prompt_toolkit.application.current import get_app
from prompt_toolkit.filters import is_searching, to_filter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.search import SearchDirection, do_incremental_search, start_search, stop_search


def load_key_bindings(app) -> KeyBindings:
    bindings = KeyBindings()

    @bindings.add("c-c", "c-c")
    def exit_(event):
        app._log("\n[Double CTRL + C] keyboard exit")
        app._cmd_exit()

    @bindings.add("c-f", filter=to_filter(not is_searching()))
    def do_find(event):
        start_search(app.log_field.control)

    @bindings.add("c-f", filter=is_searching)
    def do_exit_find(event):
        stop_search()
        get_app().layout.focus(app.input_field.control)
        get_app().invalidate()

    @bindings.add("c-z")
    def do_undo(event):
        get_app().layout.current_buffer.undo()

    @bindings.add("c-m", filter=is_searching)
    def do_find_next(event):
        do_incremental_search(direction=SearchDirection.FORWARD)

    @bindings.add("c-c")
    def do_copy(event):
        data = get_app().layout.current_buffer.copy_selection()
        get_app().clipboard.set_data(data)

    @bindings.add("c-v")
    def do_paste(event):
        get_app().layout.current_buffer.paste_clipboard_data(get_app().clipboard.get_data())

    @bindings.add("c-a")
    def do_select_all(event):
        current_buffer = get_app().layout.current_buffer
        current_buffer.cursor_position = 0
        current_buffer.start_selection()
        current_buffer.cursor_position = len(current_buffer.text)

    @bindings.add("c-t")
    def toggle_logs(event):
        app._toggle_right_pane()

    @bindings.add("c-b")
    def do_tab_navigate_left(event):
        app._tab_navigate_left()

    @bindings.add("c-n")
    def do_tab_navigate_right(event):
        app._tab_navigate_right()

    @bindings.add("f2")
    def setup(event):
        app._cmd_setup()

    @bindings.add("f5")
    def start_trading(event):
        app._handle_input("start")

    @bindings.add("f6")
    def stop_trading(event):
        app._handle_input("stop")

    @bindings.add("f9")
    def status(event):
        app._handle_input("status")

    return bindings
