"""Static gate on the package layout: public root, domain subpackages, shims.

The package root is the documented surface; everything below it is a domain
package. This test reads source text only so a broken import graph cannot hide a
layout problem. It also ratchets the size of the modules that are deliberately
large, keeps the SysML dialect out of this package, and keeps the one-release
compatibility shims logic-free.
"""

from __future__ import annotations

import ast
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

#: Modules kept for one minor release so `pyssp_sysml2.<pkg>` imports still
#: resolve. Each maps to the :mod:`pycps_sysml2` module it re-exports.
SHIM_MODULES: dict[str, str] = {
    "model/__init__.py": "pycps_sysml2.model",
    "model/exporter.py": "pycps_sysml2.model.exporter",
    "model/loader.py": "pycps_sysml2.model.loader",
    "model/model.py": "pycps_sysml2.model.model",
    "model/names.py": "pycps_sysml2.model.names",
    "model/parser.py": "pycps_sysml2.model.parser",
    "model/variation.py": "pycps_sysml2.model.variation",
    "core/__init__.py": "pycps_sysml2.core",
    "core/control.py": "pycps_sysml2.core.control",
    "core/fmi_helpers.py": "pycps_sysml2.core.fmi_helpers",
    "metadata/__init__.py": "pycps_sysml2.metadata",
    "metadata/fmu_metadata.py": "pycps_sysml2.metadata.fmu_metadata",
    "metadata/roles.py": "pycps_sysml2.metadata.roles",
    "metadata/ssp_metadata.py": "pycps_sysml2.metadata.ssp_metadata",
    "parameters/__init__.py": "pycps_sysml2.parameters",
    "parameters/configuration.py": "pycps_sysml2.parameters.configuration",
    "parameters/constraints.py": "pycps_sysml2.parameters.constraints",
    "parameters/selection.py": "pycps_sysml2.parameters.selection",
    "parameters/variation.py": "pycps_sysml2.parameters.variation",
    "parameters/dialect/__init__.py": "pycps_sysml2.parameters.dialect",
    "parameters/dialect/composition.py": "pycps_sysml2.parameters.dialect.composition",
    "parameters/dialect/declarations.py": "pycps_sysml2.parameters.dialect.declarations",
    "parameters/dialect/mapping.py": "pycps_sysml2.parameters.dialect.mapping",
    "parameters/dialect/markers.py": "pycps_sysml2.parameters.dialect.markers",
}

#: The shimmed packages. Everything below them is a shim except the listed
#: survivors, which are real code this package still owns.
SHIMMED_PACKAGES = ("model", "core", "metadata", "parameters")
SHIM_SURVIVORS = frozenset({"core/paths.py"})
SHIM_SURVIVOR_PREFIXES = ("parameters/synthesis/",)

#: The external parser moved to ``pycps_sysml2``; nothing here may import it.
SYMLPY_IMPORT = re.compile(r"\s*(?:import|from)\s+sysmlpy\b")

#: Imports that must now name ``pycps_sysml2`` directly instead of this
#: package's shims. ``core.paths`` and ``parameters.synthesis`` stay local.
SHIM_IMPORT = re.compile(
    r"^\s*from\s+pyssp_sysml2\.(?P<pkg>model|metadata|parameters|core)"
    r"(?:\.(?P<sub>[A-Za-z_][\w.]*))?\s+import\b"
)

#: Modules that exceeded the line budget when the layout was introduced.
#: Entries must name real files and carry a one-line reason.
MAX_MODULE_LINES = 600
LARGE_MODULES: dict[str, str] = {}

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


def _is_shim(relative: str) -> bool:
    return relative in SHIM_MODULES


def _docstring_lines(text: str) -> set[int]:
    """Line numbers occupied by a module docstring, which is prose, not code."""
    tree = ast.parse(text)
    if not tree.body:
        return set()
    first = tree.body[0]
    if not (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return set()
    return set(range(first.lineno, first.end_lineno + 1))


def _is_shim_survivor(relative: str) -> bool:
    return relative in SHIM_SURVIVORS or relative.startswith(SHIM_SURVIVOR_PREFIXES)


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


def test_no_module_imports_sysmlpy_directly():
    """The parser lives in ``pycps_sysml2``; this package never sees the grammar."""
    violations = []
    for path in sorted(PACKAGE.rglob("*.py")):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if SYMLPY_IMPORT.match(line):
                violations.append(f"{path.relative_to(PACKAGE)}:{lineno}")
    assert not violations, (
        "sysmlpy is owned by pycps_sysml2; found a direct import:\n"
        + "\n".join(violations)
    )


def test_only_shims_remain_in_the_moved_packages():
    unexpected = []
    for path in sorted(PACKAGE.rglob("*.py")):
        relative = str(path.relative_to(PACKAGE))
        if relative.split("/", 1)[0] not in SHIMMED_PACKAGES:
            continue
        if _is_shim(relative) or _is_shim_survivor(relative):
            continue
        unexpected.append(relative)
    assert not unexpected, (
        "a module below a shimmed package still holds logic; move it to "
        "pycps_sysml2 or add it to SHIM_SURVIVORS:\n" + "\n".join(unexpected)
    )


def test_shims_only_re_export():
    """A shim is a docstring and one ``import *``; anything else is logic."""
    problems: list[str] = []
    for relative, source in sorted(SHIM_MODULES.items()):
        path = PACKAGE / relative
        if not path.is_file():
            problems.append(f"{relative}: missing shim module")
            continue
        text = path.read_text(encoding="utf-8")
        for token in ("def ", "class "):
            if token in text:
                problems.append(f"{relative}: shim contains {token.strip()!r}")
        imports = [
            line.strip()
            for lineno, line in enumerate(text.splitlines(), start=1)
            if lineno not in _docstring_lines(text)
            and line.strip()
            and not line.strip().startswith(('"""', "#"))
        ]
        expected = f"from {source} import *"
        if len(imports) != 1 or not imports[0].startswith(expected):
            problems.append(f"{relative}: expected one `{expected}`; got {imports}")
    assert not problems, "shims must only re-export:\n" + "\n".join(problems)


def test_src_imports_pycps_not_the_shims():
    """Only the shims may name the moved packages; real code uses pycps_sysml2."""
    violations = []
    for path in sorted((PACKAGE).rglob("*.py")):
        relative = str(path.relative_to(PACKAGE))
        if _is_shim(relative):
            continue
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            match = SHIM_IMPORT.match(line)
            if not match:
                continue
            package = match.group("pkg")
            sub = match.group("sub") or ""
            if package == "core" and sub == "paths":
                continue
            if package == "parameters" and sub.startswith("synthesis"):
                continue
            violations.append(f"{relative}:{lineno} imports pyssp_sysml2.{package}")
    assert not violations, (
        "import the owner directly (pycps_sysml2); only shims may use the "
        "compatibility path:\n" + "\n".join(violations)
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
