"""Session guard: committed fixtures must not change while the suite runs.

Goldens and shared resources are evidence. A test that rewrites them while
asserting on them turns a comparison into a tautology, and the change is easy to
miss because the run is green. So the file set under the guarded roots is hashed
at session start and again at session finish; any drift fails the session and
names the paths.

Regeneration runs are the only exception: ``UPDATE_GOLDENS=1`` (and
``UPDATE_REF=1`` for the reference tree) write by design, so the guard stays out
of the way for those.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

#: Environment variables that mean "this run is allowed to rewrite fixtures".
SKIP_ENV = ("UPDATE_GOLDENS", "UPDATE_REF")

#: Guards are per session; the root (directory) is the key.
_STATE: dict[Path, dict[str, str]] = {}


def _skipping() -> bool:
    return any(os.environ.get(name) for name in SKIP_ENV)


def _digest(root: Path) -> dict[str, str]:
    """Relative posix path -> SHA-256, ignoring bytecode caches."""
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    }


def snapshot(roots: tuple[Path, ...] | list[Path]) -> None:
    """Record the committed state of ``roots`` at session start."""
    if _skipping():
        return
    _STATE.clear()
    for root in roots:
        if root.is_dir():
            _STATE[root] = _digest(root)


def drifted() -> list[str]:
    """Every path that appeared, vanished, or changed since :func:`snapshot`."""
    changed: list[str] = []
    for root, before in _STATE.items():
        after = _digest(root) if root.is_dir() else {}
        for name in sorted(set(before) | set(after)):
            if before.get(name) != after.get(name):
                changed.append(f"{root.name}/{name}")
    return changed


def check(session: pytest.Session) -> None:
    """Fail the session when a committed fixture changed during the run."""
    changed = drifted()
    if not changed:
        return

    session.exitstatus = 1
    message = "committed fixtures changed during the run:\n" + "\n".join(
        f"  {path}" for path in changed
    )
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line(message, red=True)
    else:
        print(message)
