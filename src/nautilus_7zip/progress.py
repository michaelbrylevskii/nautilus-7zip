"""Parsing helpers for 7-Zip console progress output."""

from __future__ import annotations

import re
from dataclasses import dataclass

_PROGRESS_PATTERN = re.compile(r"(?<!\d)(100|[1-9]?\d)%")
_ANSI_ESCAPE_PATTERN = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|[@-_])")
_PROCESSED_ITEM_PATTERN = re.compile(r"(?m)^[+\-TU] ")
_CREATE_TOTAL_PATTERN = re.compile(
    r"Add new data to archive:\s+(\d+)\s+files?\b",
    re.IGNORECASE,
)
_FINISHED_TOTAL_PATTERN = re.compile(r"(?m)^Files:\s+(\d+)\s*$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class FileProgress:
    """File-count information reported by one rendered 7-Zip output chunk."""

    processed: int = 0
    total: int | None = None


def parse_progress(text: str) -> int | None:
    """Return the most recent percentage in a chunk of 7-Zip output."""

    matches = _PROGRESS_PATTERN.findall(text)
    return int(matches[-1]) if matches else None


def parse_file_progress(text: str) -> FileProgress:
    """Parse processed-item lines and a trustworthy total when available."""

    total_match = _CREATE_TOTAL_PATTERN.search(text) or _FINISHED_TOTAL_PATTERN.search(text)
    return FileProgress(
        processed=len(_PROCESSED_ITEM_PATTERN.findall(text)),
        total=int(total_match.group(1)) if total_match is not None else None,
    )


def format_duration(seconds: float) -> str:
    """Format a non-negative duration compactly for the progress window."""

    value = max(0, int(seconds))
    hours, remainder = divmod(value, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


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
