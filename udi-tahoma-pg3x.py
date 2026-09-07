#!/usr/bin/env python3
"""Somfy TaHoma NodeServer for Polyglot V3 on EISY/Polisy.

Controls shades and scenarios (RTS, io, Zigbee, and other TaHoma applications).
Phantom Blinds (RTS) is the primary application this project was built for.

(C) 2025 Stephen Jenkins

Version history: see CHANGELOG.md
"""

import os
import sys
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)

import udi_interface

from nodes import Controller

VERSION = "0.0.28"

if __name__ == "__main__":
    polyglot = None
    try:
        polyglot = udi_interface.Interface([])
        polyglot.start(VERSION)
        Controller(polyglot, "controller", "controller", "TaHoma Controller")
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        udi_interface.LOGGER.warning("Received interrupt or exit...")
        if polyglot is not None:
            polyglot.stop()
    except Exception:
        udi_interface.LOGGER.error("Fatal error starting plugin", exc_info=True)
    sys.exit(0)
