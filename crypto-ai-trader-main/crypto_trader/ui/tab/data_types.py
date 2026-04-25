from dataclasses import dataclass, field
from typing import Optional, Any, Callable


@dataclass
class CommandTab:
    name: str
    tab_index: int = 0
    is_selected: bool = False
    button: Any = None
    close_button: Any = None
    output_field: Any = None
    tab_class: Any = None
    task: Any = None
