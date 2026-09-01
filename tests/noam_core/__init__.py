"""Ensures src/ is importable whether these tests are run via pytest or via
``python3 -m unittest discover`` (see scripts/verify.sh and
archive/experiments/task0_energy/STATUS.md for why this repo cannot assume a
single shared interpreter/venv for all of its Python code)."""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
