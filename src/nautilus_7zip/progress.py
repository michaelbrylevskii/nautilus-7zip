"""Parsing helpers for 7-Zip console progress output."""

from __future__ import annotations

import re

_PROGRESS_PATTERN = re.compile(r"(?<!\d)(100|[1-9]?\d)%")
_ANSI_ESCAPE_PATTERN = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|[@-_])")


def parse_progress(text: str) -> int | None:
    """Return the most recent percentage in a chunk of 7-Zip output."""

    matches = _PROGRESS_PATTERN.findall(text)
    return int(matches[-1]) if matches else None


def render_terminal_output(text: str) -> str:
    """Render terminal cursor controls into plain text suitable for a GUI log.

    7-Zip uses backspaces to erase transient percentages and scanning counters
    before it prints a filename or summary. A terminal interprets those bytes;
    a ``Gtk.TextView`` otherwise displays them as replacement glyphs.
    """

    text = _ANSI_ESCAPE_PATTERN.sub("", text)
    rendered: list[str] = []
    cells: list[str] = []
    cursor = 0

    def write(character: str) -> None:
        nonlocal cursor
        if cursor < len(cells):
            cells[cursor] = character
        else:
            cells.append(character)
        cursor += 1

    for character in text:
        if character == "\b":
            cursor = max(0, cursor - 1)
        elif character == "\r":
            cursor = 0
        elif character == "\n":
            rendered.append("".join(cells).rstrip() + "\n")
            cells = []
            cursor = 0
        elif character == "\t":
            for _ in range(8 - cursor % 8):
                write(" ")
        elif character.isprintable():
            write(character)

    if cells:
        rendered.append("".join(cells).rstrip())
    return "".join(rendered)
