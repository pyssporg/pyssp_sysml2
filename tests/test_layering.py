"""Layering rules for the ``pyssp_standard`` consumer surface."""

from __future__ import annotations

import ast
from pathlib import Path

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
