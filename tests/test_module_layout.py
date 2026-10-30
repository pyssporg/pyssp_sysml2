"""Static gate on the package layout: public root, domain subpackages.

The package root is the documented surface; everything below it is a domain
package. This test reads source text only so a broken import graph cannot hide a
layout problem. It also ratchets the size of the modules that are deliberately
large, and keeps ``sysmlpy`` confined to ``model/parser.py``.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
PACKAGE = PROJECT / "src" / "pyssp_sysml2"

#: The documented public surface. Nothing else may sit at the package root.
ROOT_MODULES = frozenset({"__init__.py", "cli.py"})

#: Domain packages. A new top-level package is a deliberate edit to this list.
SUBPACKAGES = frozenset(
    {"core", "model", "parameters", "metadata", "artifacts", "sysml"}
)

#: The only module allowed to import the external parser.
SYMLPY_IMPORT_ALLOWLIST = frozenset({"model/parser.py"})
SYMLPY_IMPORT = re.compile(r"\s*(?:import|from)\s+sysmlpy\b")

#: Modules that exceeded the line budget when the layout was introduced.
#: Entries must name real files and carry a one-line reason.
MAX_MODULE_LINES = 600

LARGE_MODULES: dict[str, str] = {
    "model/variation.py": (
        "one raw-tree pass: variation points, configuration bodies, usage extras"
    ),
    "parameters/variation.py": (
        "one variation pass: inventory, discovery, validation, body materialisation, driver"
    ),
}

#: The parameters package deliberately has no flat re-export surface; callers
#: import the precise layer. A shim would undo the split silently.
PARAMETERS_FLAT_IMPORT = re.compile(
    r"^\s*from\s+(?:pyssp_sysml2\.|\.+)?parameters(?:\.(?:dialect|synthesis))?\s+import\b"
)


def _package_dirs() -> list[Path]:
    return [
        path
        for path in PACKAGE.rglob("*")
        if path.is_dir()
        and path.name != "__pycache__"
        and not path.name.startswith(".")
    ]


def test_package_root_holds_only_the_public_modules():
    files = sorted(path.name for path in PACKAGE.iterdir() if path.is_file())
    unexpected = sorted(set(files) - ROOT_MODULES)
    missing = sorted(ROOT_MODULES - set(files))
    assert not unexpected, f"modules at the package root are not public: {unexpected}"
    assert not missing, f"public modules missing from the package root: {missing}"


def test_top_level_directories_are_declared():
    dirs = sorted(
        path.name
        for path in PACKAGE.iterdir()
        if path.is_dir()
        and path.name != "__pycache__"
        and not path.name.startswith(".")
    )
    unexpected = sorted(set(dirs) - SUBPACKAGES)
    missing = sorted(SUBPACKAGES - set(dirs))
    assert not unexpected, f"undeclared top-level packages: {unexpected}"
    assert not missing, f"declared packages missing: {missing}"


def test_every_subpackage_has_an_init():
    missing = [
        str(path.relative_to(PROJECT))
        for path in _package_dirs()
        if not (path / "__init__.py").is_file()
    ]
    assert not missing, "directory without __init__.py:\n" + "\n".join(missing)


def test_sysmlpy_is_only_imported_by_the_parser():
    violations = []
    for path in sorted(PACKAGE.rglob("*.py")):
        relative = str(path.relative_to(PACKAGE))
        if relative in SYMLPY_IMPORT_ALLOWLIST:
            continue
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if SYMLPY_IMPORT.match(line):
                violations.append(f"{relative}:{lineno}")
    assert not violations, (
        "only model/parser.py may import sysmlpy; found:\n" + "\n".join(violations)
    )


def test_large_modules_are_declared():
    oversized: dict[str, int] = {}
    for path in PACKAGE.rglob("*.py"):
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines > MAX_MODULE_LINES:
            oversized[str(path.relative_to(PACKAGE))] = lines
    undeclared = sorted(set(oversized) - set(LARGE_MODULES))
    assert not undeclared, (
        f"module over {MAX_MODULE_LINES} lines is not in LARGE_MODULES: "
        f"{[(name, oversized[name]) for name in undeclared]}"
    )


def test_large_module_entries_are_real_and_explained():
    stale = [
        name
        for name, reason in LARGE_MODULES.items()
        if not (PACKAGE / name).is_file()
    ]
    assert not stale, f"LARGE_MODULES names files that do not exist: {stale}"
    unexplained = [
        name for name, reason in LARGE_MODULES.items() if not reason.strip() or "\n" in reason
    ]
    assert not unexplained, f"LARGE_MODULES entries need a one-line reason: {unexplained}"


def test_parameters_is_imported_by_the_precise_layer():
    """No flat ``pyssp_sysml2.parameters`` import: a shim would hide the split."""
    violations = []
    for root in (PACKAGE, PROJECT / "tests"):
        for path in sorted(root.rglob("*.py")):
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if PARAMETERS_FLAT_IMPORT.match(line):
                    violations.append(f"{path.relative_to(PROJECT)}:{lineno}")
    assert not violations, (
        "import the precise parameters layer, not the package root:\n"
        + "\n".join(violations)
    )
