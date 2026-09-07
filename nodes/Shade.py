"""Module for Somfy TaHoma Shade nodes in a Polyglot v3 NodeServer.

(C) 2025 Stephen Jenkins
"""

from threading import Thread, Timer

import udi_interface

from utils.exec_status import (
    LAST_CMD_EXEC_MOVEPCT,
    LAST_CMD_EXEC_NONE,
    LAST_CMD_FAILED,
    LAST_CMD_NONE,
    LAST_CMD_PENDING,
    last_cmd_exec_label,
    tahoma_command_to_last_cmd_exec,
)
from utils.node_funcs import FieldSpec, load_persistent_data, store_values
from utils.rts_move import (
    DEFAULT_SPAN_SECONDS,
    compute_move_duration_seconds,
    direction_to_tahoma_command,
    parse_span_command,
    validate_move_direction,
    validate_move_percent,
    validate_span_seconds,
)
from utils.device_capabilities import (
    CMD_CLOSURE,
    CMD_DEPLOYMENT,
    CMD_ORIENTATION,
    GV6_UNKNOWN,
    POSITION_NA,
    STATE_BATTERY,
    STATE_CLOSURE,
    STATE_DEPLOYMENT,
    STATE_RSSI,
    STATE_STATUS,
    STATE_TILT,
    battery_value_to_gv6,
    build_device_profile,
    normalize_states,
    profile_from_map,
)

LOGGER = udi_interface.LOGGER

# RTS shade: span time, battery, last command, open/close/stop/MY, move-by-%
SHADE_RTS_DRIVERS = [
    {"driver": "GV0", "value": 0, "uom": 107, "name": "Shade Id"},
    {
        "driver": "GV1",
        "value": DEFAULT_SPAN_SECONDS,
        "uom": 58,
        "name": "Total Span Move Time",
    },
    {"driver": "GV6", "value": GV6_UNKNOWN, "uom": 25, "name": "Battery Status"},
    {"driver": "GV7", "value": LAST_CMD_NONE, "uom": 25, "name": "Last Command"},
    {
        "driver": "GV8",
        "value": LAST_CMD_EXEC_NONE,
        "uom": 25,
        "name": "Last Command Executed",
    },
]

RTS_FIELDS: dict[str, FieldSpec] = {
    "span_seconds": FieldSpec(
        driver="GV1", default=DEFAULT_SPAN_SECONDS, data_type="state"
    ),
}

# Shared driver definitions (full generic UI)
SHADE_DRIVERS_FULL = [
    {"driver": "GV0", "value": 0, "uom": 107, "name": "Shade Id"},
    {"driver": "ST", "value": 0, "uom": 2, "name": "In Motion"},
    {"driver": "GV1", "value": 0, "uom": 107, "name": "Room Id"},
    {"driver": "GV2", "value": POSITION_NA, "uom": 2, "name": "Primary"},
    {"driver": "GV3", "value": POSITION_NA, "uom": 2, "name": "Secondary"},
    {"driver": "GV4", "value": POSITION_NA, "uom": 2, "name": "Tilt"},
    {"driver": "GV5", "value": 0, "uom": 25, "name": "Protocol"},
    {"driver": "GV6", "value": GV6_UNKNOWN, "uom": 25, "name": "Battery Status"},
    {"driver": "GV7", "value": LAST_CMD_NONE, "uom": 25, "name": "Last Command"},
    {
        "driver": "GV8",
        "value": LAST_CMD_EXEC_NONE,
        "uom": 25,
        "name": "Last Command Executed",
    },
]

# TaHoma state name -> (driver, uom when value present)
_STATE_DRIVER_MAP = {
    STATE_CLOSURE: ("GV2", 100),
    STATE_DEPLOYMENT: ("GV3", 100),
    STATE_TILT: ("GV4", 100),
    STATE_STATUS: ("ST", 2),
    STATE_RSSI: ("GV11", 25),
}


class Shade(udi_interface.Node):
    """TaHoma shade node using a generic full-UI profile unless narrowed by discovery."""

    id = "shadeid"

    def __init__(self, poly, primary, address, name, sid):
        super().__init__(poly, primary, address, name)
        self.poly = poly
        self.primary = primary
        self.controller = poly.getNode(self.primary)
        self.address = address
        self.name = name
        self.sid = sid
        self.device_url = sid if isinstance(sid, str) and "://" in sid else None
        self.profile = None

        self.lpfx = f"{address}:{name}"
        self.event_polling_in = False
        self._event_polling_thread = None

        self.poly.subscribe(self.poly.START, self.start, address)
        self.poly.subscribe(self.poly.POLL, self.poll)

    def _load_profile(self):
        """Load or rebuild DeviceProfile from controller devices_map."""
        shade_data = self.controller.get_shade_data(self.sid)
        if shade_data and shade_data.get("profile"):
            self.profile = profile_from_map(shade_data["profile"])
            return
        device = shade_data.get("device") if shade_data else None
        if device:
            self.profile = build_device_profile(device)
            self.controller.update_shade_data(
                self.sid, {"profile": self._profile_map()}
            )
        else:
            from utils.device_capabilities import DeviceProfile

            self.profile = DeviceProfile(
                protocol="unknown",
                controllable_name="",
                ui_class="",
                widget="",
            )

    def _profile_map(self):
        from utils.device_capabilities import profile_to_map

        return profile_to_map(self.profile)

    def start(self):
        self.controller.ready_event.wait()

        if not self.device_url:
            device_url_key = f"device_url_{self.address}"
            if device_url_key in self.controller.Data:
                self.device_url = self.controller.Data[device_url_key]
                self.sid = self.device_url
                LOGGER.info(f"{self.lpfx}: Restored device_url: {self.device_url}")
            else:
                LOGGER.error(
                    f"{self.lpfx}: Could not recover device_url - not in custom data"
                )

        if self.device_url:
            device_url_key = f"device_url_{self.address}"
            self.controller.Data[device_url_key] = self.device_url

        self._load_profile()
        self._apply_profile_drivers()
        self.setDriver("GV8", LAST_CMD_EXEC_NONE, report=True, force=True, uom=25)

        if self.device_url:
            device_id_hash = abs(hash(self.device_url)) % 9999999
            self.setDriver("GV0", device_id_hash, report=True, force=True)
        else:
            self.setDriver("GV0", self.sid, report=True, force=True)

        self.updateData()
        LOGGER.info(
            f"{self.lpfx}: profile proto={self.profile.protocol} "
            f"pos_fb={self.profile.has_position_feedback} "
            f"controllable={self.profile.controllable_name}"
        )

    def poll(self, flag):
        if not self.controller.ready_event:
            LOGGER.error(f"Node not ready yet, exiting {self.lpfx}")
            return
        if "shortPoll" in flag:
            LOGGER.debug(f"shortPoll shade {self.lpfx}")

    def _apply_profile_drivers(self):
        """Set protocol/battery and N/A placeholders for axes without feedback."""
        if not self.profile:
            return

        self.setDriver("GV5", self.profile.protocol_gv5, report=True, force=True)
        self.setDriver("GV6", self.profile.battery_gv6, report=True, force=True)

        if not self.profile.has_position_feedback:
            if self.profile.show_primary:
                self.setDriver("GV2", POSITION_NA, report=True, force=True, uom=2)
            if self.profile.show_secondary:
                self.setDriver("GV3", POSITION_NA, report=True, force=True, uom=2)
            if self.profile.show_tilt:
                self.setDriver("GV4", POSITION_NA, report=True, force=True, uom=2)

    def _set_position_na(self, driver_key: str):
        self.setDriver(driver_key, POSITION_NA, report=True, force=False, uom=2)

    def set_last_command(self, status: int):
        """Update GV7 Last Command driver (EXECSTAT uom 25)."""
        self.setDriver("GV7", status, report=True, force=False, uom=25)

    def set_last_command_executed(self, status: int):
        """Update GV8 Last Command Executed driver (SHADECMDEXEC uom 25)."""
        self.setDriver("GV8", status, report=True, force=False, uom=25)

    def updateData(self):
        try:
            shade_data = self.controller.get_shade_data(self.sid)
            if not shade_data:
                LOGGER.warning(f"shade {self.sid} no data found in devices_map")
                return False

            device = shade_data.get("device")
            if not device:
                LOGGER.warning(f"shade {self.sid} no device object in shade_data")
                return False

            label = getattr(device, "label", None) or shade_data.get("label")
            if label and self.name != label:
                LOGGER.info(f"Name changed current:{self.name} new:{label}")
                self.rename(label)

            self._load_profile()
            self._apply_profile_drivers()
            self.sync_states_from_device(device)
            self.reportCmd("DOF", 2)
            return True
        except Exception as ex:
            LOGGER.error(f"shade {self.sid} updateData error: {ex}", exc_info=True)
            return False

    def sync_states_from_device(self, device=None):
        """Push drivers from cached TaHoma device.states."""
        if device is None:
            shade_data = self.controller.get_shade_data(self.sid)
            device = shade_data.get("device") if shade_data else None
        if not device or not getattr(device, "states", None):
            return
        self.update_drivers_from_states(device.states)

    def update_drivers_from_states(self, states):
        """Update node drivers from TaHoma states (device.states or SSE event)."""
        if not self.profile:
            self._load_profile()

        state_map = normalize_states(states)
        if not state_map:
            return

        LOGGER.debug(f"Updating drivers for {self.name} from {len(state_map)} states")

        for state_name, value in state_map.items():
            if state_name == STATE_BATTERY:
                gv6 = battery_value_to_gv6(value)
                self.setDriver("GV6", gv6, report=True, force=False)
                if self.profile:
                    self.profile.battery_gv6 = gv6
                continue

            if state_name not in _STATE_DRIVER_MAP:
                continue

            driver_key, uom = _STATE_DRIVER_MAP[state_name]
            if value is None:
                continue

            if state_name == STATE_STATUS:
                driver_value = 0 if value == "available" else 1
            elif state_name == STATE_RSSI:
                rssi_map = {
                    "verylow": 0,
                    "low": 1,
                    "normal": 2,
                    "good": 3,
                    "verygood": 4,
                    "excellent": 5,
                }
                driver_value = rssi_map.get(str(value).lower(), 2)
            else:
                try:
                    driver_value = int(value)
                except (TypeError, ValueError):
                    continue
                if not self.profile.has_position_feedback:
                    continue

            self.setDriver(
                driver_key, driver_value, report=True, force=False, uom=uom
            )

        if not self.profile.has_position_feedback:
            self._apply_profile_drivers()

    def updatePositions(self, positions):
        """Legacy path: update controller cache and position drivers when values exist."""
        LOGGER.info(f"shade:{self.sid}, positions:{positions}")
        self.controller.update_shade_data(self.sid, {"positions": positions})

        if not self.profile:
            self._load_profile()

        axis_map = [
            ("primary", "GV2", self.profile.show_primary),
            ("secondary", "GV3", self.profile.show_secondary),
            ("tilt", "GV4", self.profile.show_tilt),
        ]
        for key, driver_key, show in axis_map:
            if not show:
                continue
            pos_value = positions.get(key)
            if pos_value is None:
                if not self.profile.has_position_feedback:
                    self._set_position_na(driver_key)
            else:
                self.setDriver(driver_key, int(pos_value), report=True, force=False, uom=100)
        return True

    def cmdOpen(self, command):
        LOGGER.info(f"cmd Shade Open {self.lpfx}, {command}")
        self.execute_tahoma_command("open", [])
        self.reportCmd("OPEN", 2)

    def cmdClose(self, command):
        LOGGER.info(f"cmd Shade Close {self.lpfx}, {command}")
        self.execute_tahoma_command("close", [])
        self.reportCmd("CLOSE", 2)

    def cmdStop(self, command):
        LOGGER.info(f"cmd Shade Stop {self.lpfx}, {command}")
        self.execute_tahoma_command("stop", [])
        self.reportCmd("STOP", 2)

    def cmdTiltOpen(self, command):
        LOGGER.info(f"cmd Shade TiltOpen {self.lpfx}, {command}")
        if self.profile and not self.profile.supports_set_orientation:
            LOGGER.warning(f"{self.lpfx}: tilt open not reported by gateway")
        self.execute_tahoma_command("setOrientation", [50])
        self.reportCmd("TILTOPEN", 2)

    def cmdTiltClose(self, command):
        LOGGER.info(f"cmd Shade TiltClose {self.lpfx}, {command}")
        if self.profile and not self.profile.supports_set_orientation:
            LOGGER.warning(f"{self.lpfx}: tilt close not reported by gateway")
        self.execute_tahoma_command("setOrientation", [0])
        self.reportCmd("TILTCLOSE", 2)

    def cmdMy(self, command):
        LOGGER.info(f"cmd Shade MY {self.lpfx}, {command}")
        self.execute_tahoma_command("my", [])
        self.reportCmd("MY", 2)

    def query(self, command=None):
        LOGGER.info(f"cmd Query {self.lpfx}, {command}")
        self.updateData()
        self.reportDrivers()

    def cmdSetpos(self, command=None):
        LOGGER.info(f"cmdSetpos {self.lpfx}, {command}")
        if not command:
            LOGGER.error("No positions given")
            return

        if not self.profile:
            self._load_profile()

        try:
            query = command.get("query", {})
            key_map = {
                "SETPRIM.uom100": "primary",
                "SETSECO.uom100": "secondary",
                "SETTILT.uom100": "tilt",
            }
            pos = {
                name: int(query[key]) for key, name in key_map.items() if key in query
            }
            if pos:
                self.set_tahoma_positions(pos)
            else:
                LOGGER.error("Shade Setpos --nothing to set--")
        except (ValueError, TypeError, KeyError) as ex:
            LOGGER.error(f"Shade Setpos failed {self.lpfx}: {ex}", exc_info=True)

    def set_tahoma_positions(self, pos):
        if not self.profile:
            self._load_profile()

        if "primary" in pos:
            if self.profile.supports_set_closure:
                self.execute_tahoma_command(CMD_CLOSURE, [pos["primary"]])
            else:
                LOGGER.warning(
                    f"{self.lpfx}: setClosure not available; use Open/Close/Stop/MY"
                )

        if "secondary" in pos:
            if self.profile.supports_set_deployment:
                self.execute_tahoma_command(CMD_DEPLOYMENT, [pos["secondary"]])
            else:
                LOGGER.warning(f"{self.lpfx}: setDeployment not available on device")

        if "tilt" in pos:
            if self.profile.supports_set_orientation:
                self.execute_tahoma_command(CMD_ORIENTATION, [pos["tilt"]])
            else:
                LOGGER.warning(f"{self.lpfx}: setOrientation not available on device")

    def execute_tahoma_command(
        self, command_name, parameters, *, update_last_cmd_exec: bool = True
    ):
        import asyncio

        if update_last_cmd_exec:
            exec_value = tahoma_command_to_last_cmd_exec(command_name)
            if exec_value is not None:
                self.set_last_command_executed(exec_value)
                LOGGER.info(
                    f"{self.lpfx} Last Command Executed: "
                    f"{last_cmd_exec_label(exec_value)}"
                )

        try:
            exec_id = asyncio.run_coroutine_threadsafe(
                self.controller.tahoma_client.execute_command(
                    device_url=self.device_url,
                    command_name=command_name,
                    parameters=parameters,
                    label="ISY Control",
                ),
                self.controller.mainloop,
            ).result(timeout=10)

            if exec_id:
                self.set_last_command(LAST_CMD_PENDING)
                self.controller.track_execution(
                    exec_id, self.address, self.device_url
                )
                LOGGER.info(
                    f"TaHoma command '{command_name}' executed on {self.name} "
                    f"(exec: {exec_id})"
                )
            else:
                self.set_last_command(LAST_CMD_FAILED)
                LOGGER.warning(
                    f"TaHoma command '{command_name}' failed on {self.name}"
                )
            return exec_id
        except Exception as e:
            self.set_last_command(LAST_CMD_FAILED)
            LOGGER.error(
                f"Error executing TaHoma command '{command_name}' on {self.name}: {e}",
                exc_info=True,
            )
            return None

    drivers = SHADE_DRIVERS_FULL

    commands = {
        "OPEN": cmdOpen,
        "CLOSE": cmdClose,
        "STOP": cmdStop,
        "MY": cmdMy,
        "TILTOPEN": cmdTiltOpen,
        "TILTCLOSE": cmdTiltClose,
        "QUERY": query,
        "SETPOS": cmdSetpos,
    }


class ShadeNoTilt(Shade):
    """Backward-compatible nodedef; discovery uses generic Shade."""

    id = "shadenotiltid"
    drivers = SHADE_DRIVERS_FULL


class ShadeOnlyPrimary(Shade):
    """Backward-compatible nodedef; discovery uses generic Shade."""

    id = "shadeonlyprimid"
    drivers = SHADE_DRIVERS_FULL


class ShadeRts(Shade):
    """RTS shade node: span time, open/close/stop/MY, and timed move-by-percent."""

    id = "shadertsid"

    drivers = SHADE_RTS_DRIVERS

    def __init__(self, poly, primary, address, name, sid):
        super().__init__(poly, primary, address, name, sid)
        self.data = {field: spec.default for field, spec in RTS_FIELDS.items()}
        self._move_pct_timer: Timer | None = None
        self.poly.subscribe(self.poly.STOP, self.stop, address)

    def start(self):
        self.controller.ready_event.wait()
        load_persistent_data(self, RTS_FIELDS)
        super().start()

    def stop(self):
        self._cancel_move_pct_timer()
        LOGGER.info(f"stop: {self.lpfx}")

    def _cancel_move_pct_timer(self):
        if self._move_pct_timer is not None:
            self._move_pct_timer.cancel()
            self._move_pct_timer = None

    def execute_tahoma_command(
        self, command_name, parameters, *, update_last_cmd_exec: bool = True
    ):
        self._cancel_move_pct_timer()
        return super().execute_tahoma_command(
            command_name, parameters, update_last_cmd_exec=update_last_cmd_exec
        )

    def _apply_span_seconds(self, span: int) -> None:
        """Persist span time and push GV1 to the ISY."""
        self.data["span_seconds"] = span
        store_values(self)
        self.setDriver("GV1", span, report=True, force=True, uom=58)
        LOGGER.info(f"{self.lpfx}: total span move time set to {span}s")

    def cmdSetspan(self, command=None):
        LOGGER.info(f"cmd Set Span {self.lpfx}, {command}")
        if not command:
            LOGGER.error(f"{self.lpfx}: SETSPAN missing command payload")
            return
        try:
            span_raw = parse_span_command(command)
            if span_raw is None:
                LOGGER.error(f"{self.lpfx}: SETSPAN missing span value")
                return
            span = validate_span_seconds(span_raw)
        except (TypeError, ValueError) as ex:
            LOGGER.error(f"{self.lpfx}: SETSPAN invalid span: {ex}")
            return

        self._apply_span_seconds(span)
        self.reportCmd("SETSPAN", 2)

    def cmdMovepct(self, command=None):
        LOGGER.info(f"cmd Move By Percent {self.lpfx}, {command}")
        if not command:
            LOGGER.error(f"{self.lpfx}: MOVEPCT missing command payload")
            return
        try:
            query = command.get("query", {})
            pct_raw = query.get("PCT.uom100")
            dir_raw = query.get("DIR.uom25")
            if pct_raw is None or dir_raw is None:
                LOGGER.error(f"{self.lpfx}: MOVEPCT requires PCT and DIR parameters")
                return
            percent = validate_move_percent(int(pct_raw))
            direction = validate_move_direction(int(dir_raw))
            span = validate_span_seconds(self.data["span_seconds"])
        except (TypeError, ValueError) as ex:
            LOGGER.error(f"{self.lpfx}: MOVEPCT invalid parameters: {ex}")
            return

        duration = compute_move_duration_seconds(percent, span)
        tahoma_cmd = direction_to_tahoma_command(direction)
        self._cancel_move_pct_timer()
        self.set_last_command_executed(LAST_CMD_EXEC_MOVEPCT)
        LOGGER.info(
            f"{self.lpfx} Last Command Executed: "
            f"{last_cmd_exec_label(LAST_CMD_EXEC_MOVEPCT)}"
        )
        exec_id = self.execute_tahoma_command(
            tahoma_cmd, [], update_last_cmd_exec=False
        )
        if not exec_id:
            return

        LOGGER.info(
            f"{self.lpfx}: MOVEPCT {percent}% {tahoma_cmd} "
            f"(span={span}s, wait={duration}s before stop)"
        )
        self._move_pct_timer = Timer(duration, self._on_move_pct_timer)
        self._move_pct_timer.start()
        self.reportCmd("MOVEPCT", 2)

    def _on_move_pct_timer(self):
        self._move_pct_timer = None
        LOGGER.info(f"{self.lpfx}: MOVEPCT timer elapsed, sending stop")
        self.execute_tahoma_command("stop", [], update_last_cmd_exec=False)

    def _apply_profile_drivers(self):
        """RTS nodes only expose battery status (hardwired N/A for RTS)."""
        if not self.profile:
            return
        self.setDriver("GV6", self.profile.battery_gv6, report=True, force=True)

    def update_drivers_from_states(self, states):
        """Update battery only; RTS devices do not report position or motion."""
        if not self.profile:
            self._load_profile()
        state_map = normalize_states(states)
        if STATE_BATTERY not in state_map:
            return
        gv6 = battery_value_to_gv6(state_map[STATE_BATTERY])
        self.setDriver("GV6", gv6, report=True, force=False)
        self.profile.battery_gv6 = gv6


ShadeRts.commands = {
    "OPEN": ShadeRts.cmdOpen,
    "CLOSE": ShadeRts.cmdClose,
    "STOP": ShadeRts.cmdStop,
    "MY": ShadeRts.cmdMy,
    "QUERY": ShadeRts.query,
    "MOVEPCT": ShadeRts.cmdMovepct,
    "SETSPAN": ShadeRts.cmdSetspan,
}
