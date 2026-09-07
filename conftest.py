"""Test bootstrap: on the import path and a hermetic env before Django configures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

os.environ.setdefault("CONVEYOR_DEBUG", "1")
os.environ.setdefault("CONVEYOR_SECRET_KEY", "test-key-not-secret")
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")
