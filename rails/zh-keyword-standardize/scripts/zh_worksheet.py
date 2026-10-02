#!/usr/bin/env python3
"""Alias kept for older commands: runs ../../keyword-standardize/scripts/worksheet.py."""
import runpy, sys
from pathlib import Path
target = Path(__file__).resolve().parents[2] / "keyword-standardize" / "scripts" / "worksheet.py"
sys.path.insert(0, str(target.parent))
sys.argv[0] = str(target)
runpy.run_path(str(target), run_name="__main__")
