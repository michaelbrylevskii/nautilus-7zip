"""Parsing helpers for 7-Zip console progress output."""

from __future__ import annotations

import re

_PROGRESS_PATTERN = re.compile(r"(?<!\d)(100|[1-9]?\d)%")


def parse_progress(text: str) -> int | None:
    """Return the most recent percentage in a chunk of 7-Zip output."""

    matches = _PROGRESS_PATTERN.findall(text)
    return int(matches[-1]) if matches else None
