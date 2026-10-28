"""Layering rules for the ``pyssp_standard`` consumer surface."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from tests.conftest import COLLECTED_LEVELS, MIXED_FILES, MIXED_LEVELS

PROJECT = Path(__file__).resolve().parents[1]
SRC = PROJECT / "src"
TESTS = PROJECT / "tests"

#: Raw document fields that the SSD facade replaces with a neutral read path.
FORBIDDEN_XML_FIELDS = ("xml.system", "xml.version")


def _import_sites(path: Path) -> list[tuple[str, int]]:
    """Every imported module name with the line it appears on.

    Relative imports keep their leading dots.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    sites: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            sites.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * node.level
            if node.module:
                sites.append((prefix + node.module, node.lineno))
            elif node.level:
                sites.extend(
                    (prefix + alias.name, node.lineno)
                    for alias in node.names
                    if alias.name == "pyssp_standard"
                    or alias.name.startswith("pyssp_standard.")
                )
    return sites


def _submodule_sites(path: Path) -> list[str]:
    """Import sites that reach past the ``pyssp_standard`` public surface."""
    violations: list[str] = []
    for name, line in _import_sites(path):
        target = name.lstrip(".")
        if target.startswith("pyssp_standard.") or (
            name.startswith(".") and target == "pyssp_standard"
        ):
            violations.append(f"{path.relative_to(PROJECT)}:{line} imports {name}")
    return violations


def test_pyssp_standard_is_only_imported_through_its_public_surface():
    violations = [
        violation
        for root in (SRC, TESTS)
        for path in sorted(root.rglob("*.py"))
        for violation in _submodule_sites(path)
    ]
    assert not violations, (
        "a module imported a pyssp_standard submodule instead of the package "
        "top level:\n" + "\n".join(violations)
    )


def test_the_ssd_tree_is_read_through_the_facade():
    this_file = Path(__file__).resolve()
    violations = [
        f"{path.relative_to(PROJECT)}:{number} uses {field}"
        for root in (SRC, TESTS)
        for path in sorted(root.rglob("*.py"))
        if path.resolve() != this_file
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        )
        for field in FORBIDDEN_XML_FIELDS
        if field in line
    ]
    assert not violations, (
        "a module reached past the SSD facade into the raw document:\n"
        + "\n".join(violations)
    )


def test_every_collected_test_declares_exactly_one_level(
    request: pytest.FixtureRequest,
) -> None:
    """The level marker is how a reader knows what a green test is evidence for."""
    collected = request.config.stash[COLLECTED_LEVELS]
    assert collected, "collection recorded no tests"

    missing = [node for node, levels in collected.items() if not levels]
    assert not missing, (
        "test files without a level marker; add them to FILE_LEVELS in "
        "tests/conftest.py:\n" + "\n".join(sorted(missing))
    )

    wrong: list[str] = []
    for node, levels in sorted(collected.items()):
        if len(levels) == 1:
            continue
        file_name = node.split("::", 1)[0].rsplit("/", 1)[-1]
        if set(levels) == set(MIXED_LEVELS) and file_name in MIXED_FILES:
            continue
        wrong.append(f"{node}: {levels}")
    assert not wrong, (
        "a test must carry exactly one level marker, or both levels of a "
        "declared mixed file:\n" + "\n".join(wrong)
    )

    unused = [
        name
        for name in sorted(MIXED_FILES)
        if not any(node.split("::", 1)[0].endswith(name) for node in collected)
    ]
    assert not unused, f"mixed file entries with no collected tests: {unused}"


def test_the_version_has_one_source_of_truth() -> None:
    """``pyproject.toml`` reads the version from the package, not a copy."""
    import pyssp_sysml2

    tomllib = pytest.importorskip("tomllib", reason="tomllib is Python 3.11+")
    project = tomllib.loads((PROJECT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "version" not in project["project"]
    assert project["project"]["dynamic"] == ["version"]
    assert project["tool"]["setuptools"]["dynamic"]["version"] == {
        "attr": "pyssp_sysml2.__version__"
    }
    assert re.fullmatch(r"\d+\.\d+\.\d+", pyssp_sysml2.__version__)
