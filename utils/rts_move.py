"""RTS timed partial-move helpers (Move By Percent)."""

from __future__ import annotations

DEFAULT_SPAN_SECONDS = 8
MIN_SPAN_SECONDS = 1
MAX_SPAN_SECONDS = 999
MIN_MOVE_PCT = 1
MAX_MOVE_PCT = 99
MIN_MOVE_DURATION_SECONDS = 1

# MOVEDIR editor (uom 25)
MOVEDIR_UP = 0
MOVEDIR_DOWN = 1


def validate_span_seconds(span: int) -> int:
    """Return span seconds if within allowed range."""
    value = int(span)
    if value < MIN_SPAN_SECONDS or value > MAX_SPAN_SECONDS:
        raise ValueError(
            f"span seconds must be {MIN_SPAN_SECONDS}-{MAX_SPAN_SECONDS}, got {value}"
        )
    return value


def validate_move_percent(percent: int) -> int:
    """Return move percent if within allowed range."""
    value = int(percent)
    if value < MIN_MOVE_PCT or value > MAX_MOVE_PCT:
        raise ValueError(
            f"move percent must be {MIN_MOVE_PCT}-{MAX_MOVE_PCT}, got {value}"
        )
    return value


def validate_move_direction(direction: int) -> int:
    """Return move direction if Up or Down."""
    value = int(direction)
    if value not in (MOVEDIR_UP, MOVEDIR_DOWN):
        raise ValueError(f"move direction must be {MOVEDIR_UP} or {MOVEDIR_DOWN}")
    return value


def direction_to_tahoma_command(direction: int) -> str:
    """Map MOVEDIR editor value to TaHoma open/close command."""
    if direction == MOVEDIR_UP:
        return "open"
    if direction == MOVEDIR_DOWN:
        return "close"
    raise ValueError(f"invalid move direction: {direction}")


def compute_move_duration_seconds(
    percent: int,
    span_seconds: int,
    *,
    min_duration: int = MIN_MOVE_DURATION_SECONDS,
) -> int:
    """Seconds to wait before Stop for a partial RTS move."""
    pct = validate_move_percent(percent)
    span = validate_span_seconds(span_seconds)
    raw = round(pct / 100 * span)
    return max(min_duration, raw)


def parse_span_command(command: dict | None) -> int | None:
    """Extract span seconds from an ISY SETSPAN command payload."""
    if not command:
        return None
    value = command.get("value")
    if value is not None:
        return int(value)
    query = command.get("query") or {}
    for key in ("SPAN.uom58", "GV1.uom58", "SPAN", "GV1"):
        if key in query:
            return int(query[key])
    return None
