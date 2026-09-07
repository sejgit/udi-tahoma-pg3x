"""Tests for RTS move-by-percent helpers."""

import pytest

from utils.rts_move import (
    DEFAULT_SPAN_SECONDS,
    MOVEDIR_DOWN,
    MOVEDIR_UP,
    compute_move_duration_seconds,
    direction_to_tahoma_command,
    validate_move_direction,
    validate_move_percent,
    validate_span_seconds,
)


def test_default_span():
    assert DEFAULT_SPAN_SECONDS == 8


def test_compute_move_duration_rounds():
    assert compute_move_duration_seconds(50, 26) == 13
    assert compute_move_duration_seconds(1, 8) == 1
    assert compute_move_duration_seconds(99, 8) == 8


def test_compute_move_duration_minimum_one_second():
    assert compute_move_duration_seconds(1, 1) == 1


def test_validate_move_percent_rejects_out_of_range():
    with pytest.raises(ValueError):
        validate_move_percent(0)
    with pytest.raises(ValueError):
        validate_move_percent(100)


def test_validate_span_seconds_rejects_out_of_range():
    with pytest.raises(ValueError):
        validate_span_seconds(0)
    with pytest.raises(ValueError):
        validate_span_seconds(1000)


def test_direction_to_tahoma_command():
    assert direction_to_tahoma_command(MOVEDIR_UP) == "open"
    assert direction_to_tahoma_command(MOVEDIR_DOWN) == "close"


def test_validate_move_direction():
    assert validate_move_direction(0) == 0
    assert validate_move_direction(1) == 1
    with pytest.raises(ValueError):
        validate_move_direction(2)
