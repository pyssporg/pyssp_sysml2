"""Shared pytest configuration: one level marker per collected test.

Levels describe what a test is evidence for, not how long it runs:

- ``static``: inspects source or files without executing the package;
- ``unit``: one object's behaviour, no generated artifact;
- ``component``: a generated artifact (SSD, SSV, SSM, SSP, FMI, SysML) is the
  unit under test;
- ``contract``: two directions must agree (round-trip, sync);
- ``system``: the installed CLI is driven end to end.

Markers are applied by file in :data:`FILE_LEVELS` so a new test file cannot
silently arrive without a level; :func:`test_every_test_declares_one_level` in
``test_layering.py`` enforces that.

The session hooks below install the fixture-write guard: committed goldens and
shared resources are hashed before collection and re-checked at the end, so a
test that rewrites evidence fails the run instead of passing quietly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixture_guard import check as check_fixtures
from tests.fixture_guard import snapshot

#: Directories whose committed contents a test run must never rewrite.
GUARDED_ROOTS = (
    Path(__file__).resolve().parent / "fixtures",
    Path(__file__).resolve().parent / "golden",
    Path(__file__).resolve().parent / "resources",
)

#: Registered level markers, broadest last.
LEVEL_MARKERS = ("static", "unit", "component", "contract", "system")

#: Level markers for every test in a file.
FILE_LEVELS: dict[str, tuple[str, ...]] = {
    "test_cli.py": ("system",),
    "test_fmu_metadata.py": ("unit", "component"),
    "test_fixture_policy.py": ("static",),
    "test_generate_model_descriptions.py": ("component",),
    "test_generate_ssd.py": ("component",),
    "test_generate_ssp.py": ("component",),
    "test_generate_sysml.py": ("component",),
    "test_golden_artifacts.py": ("component",),
    "test_layering.py": ("static",),
    "test_module_layout.py": ("static",),
    "test_parameter_bind_orientation.py": ("unit",),
    "test_parameter_ports.py": ("unit",),
    "test_parameter_sets.py": ("component",),
    "test_roles_study.py": ("component",),
    "test_roundtrip.py": ("contract",),
    "test_ssp_metadata.py": ("unit",),
    "test_sync.py": ("contract",),
    "test_sysml_model.py": ("unit", "component"),
    "test_variation.py": ("unit", "component"),
}

#: Files whose tests genuinely span two levels; both markers, nothing else.
MIXED_LEVELS = ("component", "unit")

MIXED_FILES = frozenset(
    name
    for name, levels in FILE_LEVELS.items()
    if set(levels) == set(MIXED_LEVELS)
)

#: Collected node id -> level markers, for the meta test.
COLLECTED_LEVELS = pytest.StashKey[dict[str, tuple[str, ...]]]()


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    collected: dict[str, tuple[str, ...]] = {}
    for item in items:
        levels = FILE_LEVELS.get(item.path.name, ())
        for level in levels:
            item.add_marker(getattr(pytest.mark, level))
        collected[item.nodeid] = levels
    config.stash[COLLECTED_LEVELS] = collected


def pytest_sessionstart(session: pytest.Session) -> None:
    """Remember the committed fixtures before any test can touch them."""
    snapshot(GUARDED_ROOTS)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Fail the session if a committed fixture changed while it ran."""
    check_fixtures(session)
