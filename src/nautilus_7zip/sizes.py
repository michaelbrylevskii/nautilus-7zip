"""Human-readable binary size parsing for archive options."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal

_SIZE_PATTERN = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(b|k|kb|kib|m|mb|mib|g|gb|gib)\s*$",
    re.I,
)
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
    """Parse a size such as ``700M`` or ``1.5 GiB`` into whole bytes."""

    match = _SIZE_PATTERN.fullmatch(text)
    if match is None:
        raise ValueError("Invalid size; use a positive number followed by a unit")
    value = Decimal(match.group(1))
    if value <= 0:
        raise ValueError("Volume size must be positive")
    bytes_value = value * _UNIT_MULTIPLIERS[match.group(2).casefold()]
    return int(bytes_value.to_integral_value(rounding=ROUND_HALF_UP))
