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
    assert 'editor="SPANSEC"' in section
    assert "POSITION" not in section
    assert "TILT" not in section
    assert "SETPOS" not in section
    for cmd in ("OPEN", "CLOSE", "STOP", "MY", "QUERY", "MOVEPCT", "SETSPAN"):
        assert f'id="{cmd}"' in section
    assert 'id="PCT"' in section
    assert 'id="DIR"' in section
    assert 'init="GV1"' in section


def test_nls_rts_command_parameter_labels():
    nls = Path("profile/nls/en_us.txt").read_text()
    assert "CMDP-PCT-NAME = Move Percent" in nls
    assert "CMDP-DIR-NAME = Direction" in nls
    assert "PGM-CMD-MOVEPCT-FMT" in nls
    assert "PGM-CMD-SETSPAN-FMT" in nls


def test_nls_rts_shade_labels():
    nls = Path("profile/nls/en_us.txt").read_text()
    assert "ND-shadertsid-NAME = RTS Shade" in nls
    assert "ST-shaderts-GV1-NAME = Total Span Move Time" in nls
    assert "ST-shaderts-GV7-NAME = Last Command" in nls
    assert "ST-shaderts-GV8-NAME = Last Command Executed" in nls
    assert "SHADECMDEXEC-0 = None" in nls
    assert "SHADECMDEXEC-5 = Move By Percent" in nls
    assert "CMD-shaderts-MOVEPCT-NAME = Move By Percent" in nls
    assert "CMD-shaderts-SETSPAN-NAME = Set Span Move Time" in nls
