from __future__ import annotations

import re
from datetime import timedelta

_WINDOW_RE = re.compile(r"^\s*(\d+)\s*([smhdw])\s*$", re.IGNORECASE)
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def parse_window(spec: str) -> timedelta:
    """Parse a retention window like ``14d`` / ``36h`` / ``2w`` into a timedelta.

    Raises ``ValueError`` on anything else so a bad ``CONVEYOR_HOT_WINDOW`` fails
    loudly instead of silently pruning everything (or nothing).
    """
    match = _WINDOW_RE.match(spec)
    if not match:
        raise ValueError(
            f"invalid retention window {spec!r} — expected '<n><unit>', unit one of s/m/h/d/w"
        )
    value, unit = int(match.group(1)), match.group(2).lower()
    if value <= 0:
        raise ValueError(f"retention window must be positive, got {spec!r}")
    return timedelta(seconds=value * _UNIT_SECONDS[unit])
