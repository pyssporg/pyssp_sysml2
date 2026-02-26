"""Shared path defaults and helpers for generator CLIs."""
from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_DIR.parent
REPO_ROOT = SRC_DIR.parent

BUILD_DIR = REPO_ROOT / "build"
GENERATED_DIR = BUILD_DIR / "generated"
ARCHITECTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "aircraft_subset"
COMPOSITION_NAME = "AircraftComposition"


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_parent_dir(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
