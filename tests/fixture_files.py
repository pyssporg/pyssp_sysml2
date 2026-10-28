"""Committed test inputs and expected artifacts.

A SysML architecture is a document, so it lives in a file and is reviewed as
SysML. Only the path resolution and the comparison belong in Python. Every path
resolves from this module, never from the process cwd.
"""

from __future__ import annotations

import difflib
import string
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def fixture_path(relative: str) -> Path:
    """Absolute path of a committed fixture, given its path under ``fixtures/``."""
    return FIXTURES / relative


def fixture_text(relative: str) -> str:
    """Fixture content as it should be written: UTF-8, one trailing newline."""
    return fixture_path(relative).read_text(encoding="utf-8")


def render_fixture(relative: str, **slots: str) -> str:
    """Fill ``$slot`` / ``${slot}`` placeholders in a fixture template."""
    return string.Template(fixture_text(relative)).substitute(**slots)


def assert_matches_fixture(actual: str, relative: str) -> None:
    """Compare generated text with an expected artifact, showing a diff.

    The committed file is the oracle's expectation; the failure message is the
    change a reviewer has to accept or reject.
    """
    expected = fixture_text(relative)
    if actual == expected:
        return
    diff = difflib.unified_diff(
        expected.splitlines(keepends=True),
        actual.splitlines(keepends=True),
        fromfile=f"expected:{relative}",
        tofile="actual",
    )
    raise AssertionError(
        "generated text differs from the expected artifact:\n" + "".join(diff)
    )
