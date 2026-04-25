from prompt_toolkit.styles import Style
from prompt_toolkit.utils import is_windows


text_ui_style = {
    "&cGOLD": "gold_label",
    "&cSILVER": "silver_label",
    "&cBRONZE": "bronze_label",
}

default_ui_style = {
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

win32_code_style = {
    "output_field":               "#ansigreen",
    "input_field":                "#ansiwhite",
    "log_field":                  "#ansiwhite",
    "header":                     "#ansiwhite",
    "footer":                     "#ansiwhite",
    "search":                     "#ansigreen",
    "search.current":             "#ansigreen",
    "primary":                    "#ansigreen",
    "warning":                    "#ansibrightyellow",
    "error":                      "#ansired",
    "tab_button.focused":         "bg:#ansigreen #ansiblack",
    "tab_button":                 "bg:#ansiwhite #ansiblack",
    "dialog":                     "bg:#ansigreen",
    "dialog frame.label":         "bg:#ansiwhite #ansiblack",
    "dialog.body":                "bg:#ansiblack ",
    "dialog shadow":              "bg:#ansigreen",
    "button":                     "bg:#ansiwhite #ansiblack",
    "text-area":                  "bg:#ansiblack #ansigreen",
    "primary_label":              "bg:#ansigreen #ansiblack",
    "secondary_label":            "bg:#ansibrightyellow #ansiblack",
    "success_label":              "bg:#ansigreen #ansiblack",
    "warning_label":              "bg:#ansibrightyellow #ansiblack",
    "info_label":                 "bg:#ansiblue #ansiblack",
    "error_label":                "bg:#ansired #ansiwhite",
    "gold_label":                 "#ansiyellow",
    "silver_label":               "#ansilightgray",
    "bronze_label":               "#ansibrown",
}


def hex_to_ansi(color_hex):
    ansi_palette = {
        "000000": "ansiblack",
        "FF0000": "ansired",
        "00FF00": "ansigreen",
        "FFFF00": "ansiyellow",
        "0000FF": "ansiblue",
        "FF00FF": "ansimagenta",
        "00FFFF": "ansicyan",
        "F0F0F0": "ansigray",
        "FFFFFF": "ansiwhite",
        "FFD700": "ansiyellow",
        "C0C0C0": "ansilightgray",
        "CD7F32": "ansibrown",
    }

    color_hex = color_hex.replace('#', '')

    hex_r = int(color_hex[0:2], 16)
    hex_g = int(color_hex[2:4], 16)
    hex_b = int(color_hex[4:6], 16)

    distance_min = None
    color_ansi = "ansiwhite"

    for ansi_hex in ansi_palette:
        ansi_r = int(ansi_hex[0:2], 16)
        ansi_g = int(ansi_hex[2:4], 16)
        ansi_b = int(ansi_hex[4:6], 16)

        distance = abs(ansi_r - hex_r) + abs(ansi_g - hex_g) + abs(ansi_b - hex_b)

        if distance_min is None or distance < distance_min:
            distance_min = distance
            color_ansi = ansi_palette[ansi_hex]

    return "#" + color_ansi


def load_style():
    if is_windows():
        style = dict(win32_code_style)
        return Style.from_dict(style)
    else:
        style = dict(default_ui_style)
        return Style.from_dict(style)
