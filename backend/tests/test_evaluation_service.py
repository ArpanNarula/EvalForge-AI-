"""Wrapper so `cd backend && pytest tests/ -v` works with the shared root code."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from test_evaluation_service import *  # noqa: F401,F403

