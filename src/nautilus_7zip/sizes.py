"""Human-readable binary size parsing for archive options."""

from __future__ import annotations

import re

_SIZE_PATTERN = re.compile(r"^\s*(\d+)\s*(b|k|kb|kib|m|mb|mib|g|gb|gib)\s*$", re.I)
_UNIT_MULTIPLIERS = {
    "b": 1,
    "k": 1024,
    "kb": 1024,
    "kib": 1024,
    "m": 1024**2,
    "mb": 1024**2,
    "mib": 1024**2,
    "g": 1024**3,
    "gb": 1024**3,
    "gib": 1024**3,
}


def parse_binary_size(text: str) -> int:
    """Parse an integer size such as ``700M`` or ``2 GiB`` into bytes."""

    match = _SIZE_PATTERN.fullmatch(text)
    if match is None:
        raise ValueError("Invalid size; use an integer followed by M or G")
    value = int(match.group(1))
    if value < 1:
        raise ValueError("Volume size must be positive")
    return value * _UNIT_MULTIPLIERS[match.group(2).casefold()]
