"""TaHoma device capability helpers for shade nodes.

Builds a DeviceProfile from pyoverkiz Device objects. When data is incomplete
we default to a generic profile that exposes the full ISY UI; field feedback and
command gating tighten as discovery learns more from the gateway.

(C) 2025 Stephen Jenkins
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional

# GV5 protocol / link type (uom 25, SHADECAP NLS)
GV5_UNKNOWN = 0
GV5_RTS = 1
GV5_IO = 2
GV5_ZIGBEE = 3
GV5_OTHER = 4

# GV6 battery status (uom 25, BATTERYST NLS)
GV6_UNKNOWN = 0
GV6_NA_HARDWIRED = 255

# Position driver N/A (POSITION editor uom 2 subset 0)
POSITION_NA = 0

# TaHoma state and command names we care about
STATE_CLOSURE = "core:ClosureState"
STATE_DEPLOYMENT = "core:DeploymentState"
STATE_TILT = "core:SlateOrientationState"
STATE_BATTERY = "core:BatteryState"
STATE_STATUS = "core:StatusState"
STATE_RSSI = "core:DiscreteRSSILevelState"

CMD_CLOSURE = "setClosure"
CMD_DEPLOYMENT = "setDeployment"
CMD_ORIENTATION = "setOrientation"

# Gateway / infrastructure devices — not user shades
SKIP_CONTROLLABLE_PREFIXES = (
    "zigbee:Transceiver",
    "internal:Pod",
    "internal:Wifi",
    "ogp:Bridge",
)

BATTERY_STATE_TO_GV6: dict[str, int] = {
    "normal": 3,
    "high": 3,
    "medium": 2,
    "low": 1,
    "verylow": 1,
    "critical": 1,
    "notavailable": 0,
}


@dataclass
class DeviceProfile:
    """Resolved capabilities for one TaHoma device."""

    protocol: str
    controllable_name: str
    ui_class: str
    widget: str
    protocol_gv5: int = GV5_UNKNOWN
    command_names: set[str] = field(default_factory=set)
    state_names: set[str] = field(default_factory=set)
    # Generic UI: show all axes unless we learn the device cannot use them
    show_primary: bool = True
    show_secondary: bool = True
    show_tilt: bool = True
    has_position_feedback: bool = False
    supports_set_closure: bool = True
    supports_set_deployment: bool = True
    supports_set_orientation: bool = True
    battery_gv6: int = GV6_UNKNOWN

    @property
    def is_rts(self) -> bool:
        return self.protocol == "rts"


def protocol_from_device_url(device_url: str) -> str:
    """Return protocol segment from a TaHoma device URL (e.g. rts, io)."""
    if "://" in device_url:
        return device_url.split("://", 1)[0].lower()
    return "unknown"


def protocol_to_gv5(protocol: str) -> int:
    """Map protocol string to GV5 driver index."""
    return {
        "rts": GV5_RTS,
        "io": GV5_IO,
        "zigbee": GV5_ZIGBEE,
    }.get(protocol, GV5_OTHER)


def should_create_shade_node(device: Any) -> bool:
    """Return False for gateway infrastructure devices that are not shades."""
    device_url = getattr(device, "device_url", "") or ""
    if device_url.startswith("internal://"):
        return False

    controllable = getattr(device, "controllable_name", "") or ""
    for prefix in SKIP_CONTROLLABLE_PREFIXES:
        if controllable.startswith(prefix):
            return False
    return True


def _command_names(device: Any) -> set[str]:
    definition = getattr(device, "definition", None)
    if not definition:
        return set()
    commands = getattr(definition, "commands", None)
    if not commands:
        return set()
    if hasattr(commands, "keys"):
        return set(commands.keys())
    names: set[str] = set()
    for command in commands:
        if isinstance(command, str):
            names.add(command)
        elif hasattr(command, "command_name"):
            names.add(command.command_name)
    return names


def _state_names(device: Any) -> set[str]:
    states = getattr(device, "states", None)
    if not states:
        return set()
    if hasattr(states, "keys"):
        return set(states.keys())
    names: set[str] = set()
    for state in states:
        if isinstance(state, str):
            names.add(state)
        elif hasattr(state, "name"):
            names.add(state.name)
    return names


def _state_value(device: Any, state_name: str) -> Any:
    states = getattr(device, "states", None)
    if not states:
        return None
    if hasattr(states, "get"):
        entry = states.get(state_name)
        if entry is None:
            return None
        return getattr(entry, "value", entry)
    return None


def battery_value_to_gv6(value: Any) -> int:
    """Map TaHoma core:BatteryState value to GV6 index."""
    if value is None:
        return GV6_UNKNOWN
    text = str(value).lower().strip()
    if text in BATTERY_STATE_TO_GV6:
        return BATTERY_STATE_TO_GV6[text]
    if text in ("full", "ok", "good"):
        return 3
    if text in ("plugged", "pluggedin", "mains"):
        return 4
    return GV6_UNKNOWN


def build_device_profile(device: Any) -> DeviceProfile:
    """Build a profile from a pyoverkiz Device.

    Uses a generic defaults-first model: full UI unless the gateway reports
    commands/states that narrow behavior. RTS devices get hardwired battery and
    no position feedback unless ClosureState is present.
    """
    device_url = getattr(device, "device_url", "") or ""
    protocol = protocol_from_device_url(device_url)
    commands = _command_names(device)
    states = _state_names(device)

    profile = DeviceProfile(
        protocol=protocol,
        controllable_name=getattr(device, "controllable_name", "") or "",
        ui_class=getattr(device, "ui_class", "") or "",
        widget=getattr(device, "widget", "") or "",
        protocol_gv5=protocol_to_gv5(protocol),
        command_names=commands,
        state_names=states,
    )

    has_closure_state = STATE_CLOSURE in states
    has_commands = bool(commands)

    profile.has_position_feedback = has_closure_state
    profile.supports_set_closure = (not has_commands) or (CMD_CLOSURE in commands)
    profile.supports_set_deployment = (not has_commands) or (CMD_DEPLOYMENT in commands)
    profile.supports_set_orientation = (not has_commands) or (CMD_ORIENTATION in commands)

    # RTS in the field: often empty definition.commands — open/close/stop/MY only
    if protocol == "rts":
        profile.has_position_feedback = has_closure_state
        profile.battery_gv6 = GV6_NA_HARDWIRED
        if not has_commands:
            profile.supports_set_closure = False
            profile.supports_set_deployment = False
            profile.supports_set_orientation = False
        else:
            profile.supports_set_closure = CMD_CLOSURE in commands
            profile.supports_set_deployment = CMD_DEPLOYMENT in commands
            profile.supports_set_orientation = CMD_ORIENTATION in commands

    if STATE_BATTERY in states:
        profile.battery_gv6 = battery_value_to_gv6(_state_value(device, STATE_BATTERY))
    elif protocol == "rts":
        profile.battery_gv6 = GV6_NA_HARDWIRED

    # Generic UI: always show all position fields; use N/A when no feedback
    profile.show_primary = True
    profile.show_secondary = True
    profile.show_tilt = True

    return profile


def profile_to_map(profile: DeviceProfile) -> dict[str, Any]:
    """Serialize profile for devices_map storage."""
    return {
        "protocol": profile.protocol,
        "controllable_name": profile.controllable_name,
        "ui_class": profile.ui_class,
        "widget": profile.widget,
        "protocol_gv5": profile.protocol_gv5,
        "command_names": sorted(profile.command_names),
        "state_names": sorted(profile.state_names),
        "show_primary": profile.show_primary,
        "show_secondary": profile.show_secondary,
        "show_tilt": profile.show_tilt,
        "has_position_feedback": profile.has_position_feedback,
        "supports_set_closure": profile.supports_set_closure,
        "supports_set_deployment": profile.supports_set_deployment,
        "supports_set_orientation": profile.supports_set_orientation,
        "battery_gv6": profile.battery_gv6,
    }


def profile_from_map(data: Optional[Mapping[str, Any]]) -> DeviceProfile:
    """Restore DeviceProfile from devices_map entry."""
    if not data:
        return DeviceProfile(
            protocol="unknown",
            controllable_name="",
            ui_class="",
            widget="",
        )
    return DeviceProfile(
        protocol=data.get("protocol", "unknown"),
        controllable_name=data.get("controllable_name", ""),
        ui_class=data.get("ui_class", ""),
        widget=data.get("widget", ""),
        protocol_gv5=int(data.get("protocol_gv5", GV5_UNKNOWN)),
        command_names=set(data.get("command_names", [])),
        state_names=set(data.get("state_names", [])),
        show_primary=bool(data.get("show_primary", True)),
        show_secondary=bool(data.get("show_secondary", True)),
        show_tilt=bool(data.get("show_tilt", True)),
        has_position_feedback=bool(data.get("has_position_feedback", False)),
        supports_set_closure=bool(data.get("supports_set_closure", True)),
        supports_set_deployment=bool(data.get("supports_set_deployment", True)),
        supports_set_orientation=bool(data.get("supports_set_orientation", True)),
        battery_gv6=int(data.get("battery_gv6", GV6_UNKNOWN)),
    )


def normalize_states(states: Any) -> dict[str, Any]:
    """Normalize TaHoma states (dict, list, or event payload) to name -> value."""
    result: dict[str, Any] = {}
    if not states:
        return result

    if hasattr(states, "items"):
        for name, entry in states.items():
            result[str(name)] = getattr(entry, "value", entry)
        return result

    if isinstance(states, Mapping):
        for name, entry in states.items():
            result[str(name)] = getattr(entry, "value", entry) if not isinstance(
                entry, (str, int, float, bool)
            ) else entry
        return result

    for entry in states:
        if isinstance(entry, str):
            continue
        name = getattr(entry, "name", None)
        if name:
            result[str(name)] = getattr(entry, "value", None)
    return result


def format_discovery_summary(device: Any, profile: DeviceProfile) -> str:
    """One-line discovery summary for INFO logs (user feedback in the field)."""
    cmds = ",".join(sorted(profile.command_names)) or "none"
    sts = ",".join(sorted(profile.state_names)) or "none"
    return (
        f"{device.label}: {profile.controllable_name} "
        f"proto={profile.protocol} ui={profile.ui_class} "
        f"cmds=[{cmds}] states=[{sts}] "
        f"pos_fb={profile.has_position_feedback} batt_gv6={profile.battery_gv6}"
    )


def log_device_discovery(device: Any, profile: DeviceProfile, logger: Any) -> None:
    """Log device discovery at DEBUG; single INFO line for field diagnostics."""
    logger.info(format_discovery_summary(device, profile))
    logger.debug("Device URL: %s", device.device_url)
    logger.debug("  Widget: %s", profile.widget)
    logger.debug("  Commands: %s", profile.command_names)
    logger.debug("  States: %s", profile.state_names)
