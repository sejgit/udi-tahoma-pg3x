"""Tests for device_capabilities helpers."""

from unittest.mock import Mock

from pyoverkiz.models import CommandDefinition

from utils.device_capabilities import (
    GV5_RTS,
    GV6_NA_HARDWIRED,
    POSITION_NA,
    STATE_CLOSURE,
    build_device_profile,
    battery_value_to_gv6,
    normalize_states,
    profile_from_map,
    profile_to_map,
    protocol_from_device_url,
    should_create_shade_node,
)


def _device(
    url="rts://2075-3852-5398/16758638",
    controllable="rts:ExteriorBlindRTSComponent",
    ui_class="ExteriorScreen",
    widget="UpDownExteriorScreen",
    commands=None,
    states=None,
):
    device = Mock()
    device.device_url = url
    device.controllable_name = controllable
    device.ui_class = ui_class
    device.widget = widget
    device.label = "North Lite"
    device.definition = Mock()
    device.definition.commands = commands or {}
    device.states = states or {}
    return device


class TestShouldCreateShadeNode:
    def test_rts_blind_is_shade(self):
        assert should_create_shade_node(_device()) is True

    def test_internal_pod_skipped(self):
        assert (
            should_create_shade_node(
                _device(
                    url="internal://2075-3852-5398/pod/0",
                    controllable="internal:PodV3Component",
                )
            )
            is False
        )

    def test_zigbee_transceiver_skipped(self):
        assert (
            should_create_shade_node(
                _device(
                    url="zigbee://2075-3852-5398/65535",
                    controllable="zigbee:TransceiverV3_0Component",
                )
            )
            is False
        )

    def test_ogp_bridge_skipped(self):
        assert (
            should_create_shade_node(
                _device(
                    url="ogp://2076-5923-5791/0003FEF3",
                    controllable="ogp:Bridge",
                    ui_class="ProtocolGateway",
                )
            )
            is False
        )


class TestBuildDeviceProfile:
    def test_rts_exterior_blind_from_logs(self):
        profile = build_device_profile(_device())
        assert profile.protocol == "rts"
        assert profile.protocol_gv5 == GV5_RTS
        assert profile.battery_gv6 == GV6_NA_HARDWIRED
        assert profile.has_position_feedback is False
        assert profile.show_primary is True
        assert profile.command_names == set()
        assert profile.supports_set_closure is False

    def test_command_definition_list_from_gateway(self):
        commands = [
            CommandDefinition(command_name="open", nparams=0),
            CommandDefinition(command_name="close", nparams=0),
            CommandDefinition(command_name="stop", nparams=0),
        ]
        profile = build_device_profile(_device(commands=commands))
        assert profile.command_names == {"open", "close", "stop"}
        assert profile.supports_set_closure is False

    def test_io_with_closure_state_has_feedback(self):
        state = Mock(value=50)
        profile = build_device_profile(
            _device(
                url="io://gw/123",
                controllable="io:RollerShutterGenericIOComponent",
                states={STATE_CLOSURE: state},
            )
        )
        assert profile.protocol == "io"
        assert profile.has_position_feedback is True

    def test_battery_state_mapped(self):
        state = Mock(value="low")
        profile = build_device_profile(
            _device(states={"core:BatteryState": state}),
        )
        assert profile.battery_gv6 == 1


class TestNormalizeStates:
    def test_dict_states(self):
        state = Mock(value=75)
        assert normalize_states({STATE_CLOSURE: state}) == {STATE_CLOSURE: 75}


class TestBatteryMapping:
    def test_low(self):
        assert battery_value_to_gv6("low") == 1


class TestProfileRoundTrip:
    def test_to_from_map(self):
        profile = build_device_profile(_device())
        restored = profile_from_map(profile_to_map(profile))
        assert restored.protocol_gv5 == GV5_RTS
        assert restored.battery_gv6 == GV6_NA_HARDWIRED


class TestProtocol:
    def test_rts_url(self):
        assert protocol_from_device_url("rts://2075-3852-5398/1") == "rts"
