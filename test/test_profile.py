"""Validate ISY profile files against node server code."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "profile"
NODEDEFS = PROFILE / "nodedef" / "nodedefs.xml"
NLS = PROFILE / "nls" / "en_us.txt"
EDITORS = PROFILE / "editor" / "editors.xml"
VERSION_FILE = PROFILE / "version.txt"
ENTRY = ROOT / "udi-tahoma-pg3x.py"

NODE_COMMANDS = {
    "hdctrl": {"QUERY", "DISCOVER", "UPDATE_PROFILE", "REMOVE_NOTICES_ALL"},
    "sceneid": {"ACTIVATE", "QUERY"},
    "shadeid": {
        "OPEN",
        "CLOSE",
        "STOP",
        "MY",
        "TILTOPEN",
        "TILTCLOSE",
        "QUERY",
        "SETPOS",
    },
    "shadenotiltid": {"OPEN", "CLOSE", "STOP", "MY", "QUERY", "SETPOS"},
    "shadeonlyprimid": {"OPEN", "CLOSE", "STOP", "MY", "QUERY", "SETPOS"},
    "shadertsid": {"OPEN", "CLOSE", "STOP", "MY", "QUERY", "MOVEPCT", "SETSPAN"},
}

REPORTED_COMMANDS = {
    "sceneid": {"ACTIVATE"},
    "shadeid": {"OPEN", "CLOSE", "STOP", "MY", "TILTOPEN", "TILTCLOSE", "DOF"},
    "shadenotiltid": {"OPEN", "CLOSE", "STOP", "MY", "DOF"},
    "shadeonlyprimid": {"OPEN", "CLOSE", "STOP", "MY", "DOF"},
    "shadertsid": {"OPEN", "CLOSE", "STOP", "MY", "DOF"},
}


def _parse_nodedefs() -> dict[str, dict[str, set[str]]]:
    tree = ET.parse(NODEDEFS)
    result: dict[str, dict[str, set[str]]] = {}
    for node in tree.getroot().findall("nodeDef"):
        node_id = node.attrib["id"]
        cmds: dict[str, set[str]] = {"sends": set(), "accepts": set()}
        for section in ("sends", "accepts"):
            container = node.find(f"cmds/{section}")
            if container is None:
                continue
            for cmd in container.findall("cmd"):
                cmds[section].add(cmd.attrib["id"])
        result[node_id] = cmds
    return result


def _editor_ids() -> set[str]:
    tree = ET.parse(EDITORS)
    return {editor.attrib["id"] for editor in tree.getroot().findall("editor")}


def _entry_version() -> str:
    text = ENTRY.read_text()
    match = re.search(r'^VERSION = "([^"]+)"', text, re.MULTILINE)
    assert match, "VERSION not found in udi-tahoma-pg3x.py"
    return match.group(1)


def test_profile_version_matches_entry_script():
    assert VERSION_FILE.exists(), "profile/version.txt is required for ISY profile sync"
    assert VERSION_FILE.read_text().strip() == _entry_version()


def test_nodedef_ids_cover_node_classes():
    nodedefs = _parse_nodedefs()
    assert set(nodedefs) == set(NODE_COMMANDS)


@pytest.mark.parametrize("node_id", sorted(NODE_COMMANDS))
def test_nodedef_accepts_match_python_commands(node_id: str):
    nodedefs = _parse_nodedefs()
    assert nodedefs[node_id]["accepts"] == NODE_COMMANDS[node_id]


@pytest.mark.parametrize("node_id", sorted(REPORTED_COMMANDS))
def test_reported_commands_are_in_sends(node_id: str):
    nodedefs = _parse_nodedefs()
    assert REPORTED_COMMANDS[node_id].issubset(nodedefs[node_id]["sends"])


def test_controller_update_profile_in_nodedef():
    nodedefs = _parse_nodedefs()
    assert "UPDATE_PROFILE" in nodedefs["hdctrl"]["accepts"]


def test_scene_activate_in_sends_and_accepts():
    nodedefs = _parse_nodedefs()
    assert "ACTIVATE" in nodedefs["sceneid"]["sends"]
    assert "ACTIVATE" in nodedefs["sceneid"]["accepts"]


def test_status_editors_exist():
    editors = _editor_ids()
    tree = ET.parse(NODEDEFS)
    used = {
        st.attrib["editor"]
        for node in tree.getroot().findall("nodeDef")
        for st in node.findall("sts/st")
    }
    missing = used - editors
    assert not missing, f"Missing editor definitions: {sorted(missing)}"


def test_nls_has_controller_status_labels():
    nls = NLS.read_text()
    assert "ST-ctl-ST-NAME = Connection" in nls
    assert "ST-ctl-GV0-NAME = Number Of Nodes" in nls
