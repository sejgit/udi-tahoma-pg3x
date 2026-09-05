"""Tests for RTS shade profile (no udi_interface import required)."""

from pathlib import Path


def test_nodedef_rts_shade_minimal_status():
    xml = Path("profile/nodedef/nodedefs.xml").read_text()
    start = xml.index('id="shadertsid"')
    section = xml[start : xml.index("</nodeDef>", start)]
    assert 'editor="ID"' in section
    assert 'editor="BATTERYST"' in section
    assert 'editor="EXECSTAT"' in section
    assert 'editor="SHADECMDEXEC"' in section
    assert "POSITION" not in section
    assert "TILT" not in section
    assert "SETPOS" not in section
    for cmd in ("OPEN", "CLOSE", "STOP", "MY", "QUERY"):
        assert f'id="{cmd}"' in section


def test_nls_rts_shade_labels():
    nls = Path("profile/nls/en_us.txt").read_text()
    assert "ND-shadertsid-NAME = RTS Shade" in nls
    assert "ST-shaderts-GV7-NAME = Last Command" in nls
    assert "ST-shaderts-GV8-NAME = Last Command Executed" in nls
    assert "SHADECMDEXEC-0 = None" in nls
