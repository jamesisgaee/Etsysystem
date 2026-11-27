#!/usr/bin/env python3
"""Compatibility wrapper. The simple board is rebuilt by build_board.py."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent / "build_board.py"), run_name="__main__")
