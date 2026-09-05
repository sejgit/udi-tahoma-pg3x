"""TaHoma execution status mapping for shade Last Command drivers (GV7, GV8)."""

from __future__ import annotations

from pyoverkiz.enums.execution import ExecutionState

# GV7 Last Command (uom 25, EXECSTAT NLS)
LAST_CMD_NONE = 0
LAST_CMD_PENDING = 1
LAST_CMD_COMPLETED = 2
LAST_CMD_FAILED = 3

_LAST_CMD_LABELS = {
    LAST_CMD_NONE: "—",
    LAST_CMD_PENDING: "Pending",
    LAST_CMD_COMPLETED: "Completed",
    LAST_CMD_FAILED: "Failed",
}

_PENDING_STATES = frozenset(
    {
        ExecutionState.UNKNOWN,
        ExecutionState.INITIALIZED,
        ExecutionState.TRANSMITTED,
        ExecutionState.IN_PROGRESS,
        ExecutionState.QUEUED_GATEWAY_SIDE,
        ExecutionState.QUEUED_SERVER_SIDE,
    }
)
_FAILED_STATES = frozenset({ExecutionState.FAILED, ExecutionState.NOT_TRANSMITTED})


def last_cmd_label(status: int) -> str:
    """Return a short label for logs and diagnostics."""
    return _LAST_CMD_LABELS.get(status, str(status))


def parse_execution_state(state: ExecutionState | str | None) -> ExecutionState | None:
    """Normalize pyoverkiz execution state values."""
    if state is None:
        return None
    if isinstance(state, ExecutionState):
        return state
    try:
        return ExecutionState(state)
    except ValueError:
        return None


def execution_state_to_last_cmd(state: ExecutionState | str | None) -> int | None:
    """Map TaHoma execution state to GV7 Last Command value, or None if unchanged."""
    parsed = parse_execution_state(state)
    if parsed is None:
        return None
    if parsed == ExecutionState.COMPLETED:
        return LAST_CMD_COMPLETED
    if parsed in _FAILED_STATES:
        return LAST_CMD_FAILED
    if parsed in _PENDING_STATES:
        return LAST_CMD_PENDING
    return None


# GV8 Last Command Executed (uom 25, SHADECMDEXEC NLS)
LAST_CMD_EXEC_NONE = 0
LAST_CMD_EXEC_OPEN = 1
LAST_CMD_EXEC_CLOSE = 2
LAST_CMD_EXEC_STOP = 3
LAST_CMD_EXEC_MY = 4

_LAST_CMD_EXEC_LABELS = {
    LAST_CMD_EXEC_NONE: "None",
    LAST_CMD_EXEC_OPEN: "Open",
    LAST_CMD_EXEC_CLOSE: "Close",
    LAST_CMD_EXEC_STOP: "Stop",
    LAST_CMD_EXEC_MY: "My Position",
}

_TAHOMA_CMD_TO_LAST_CMD_EXEC = {
    "open": LAST_CMD_EXEC_OPEN,
    "close": LAST_CMD_EXEC_CLOSE,
    "stop": LAST_CMD_EXEC_STOP,
    "my": LAST_CMD_EXEC_MY,
}


def last_cmd_exec_label(status: int) -> str:
    """Return a short label for Last Command Executed logs."""
    return _LAST_CMD_EXEC_LABELS.get(status, str(status))


def tahoma_command_to_last_cmd_exec(command_name: str | None) -> int | None:
    """Map a TaHoma shade command name to GV8 value, or None if not tracked."""
    if not command_name:
        return None
    return _TAHOMA_CMD_TO_LAST_CMD_EXEC.get(command_name.strip().lower())


def scenario_parent_exec_to_last_cmd(state: ExecutionState | str | None) -> int | None:
    """Map scenario parent exec state for Last Command (GV7).

    TaHoma local API often reports spurious FAILED/INITIALIZED oscillation on the
    parent exec for persisted action groups. Child shade commands still run.
    Only COMPLETED and NOT_TRANSMITTED are treated as terminal here.
    """
    parsed = parse_execution_state(state)
    if parsed is None:
        return None
    if parsed == ExecutionState.COMPLETED:
        return LAST_CMD_COMPLETED
    if parsed == ExecutionState.NOT_TRANSMITTED:
        return LAST_CMD_FAILED
    if parsed in _PENDING_STATES:
        return LAST_CMD_PENDING
    return None
