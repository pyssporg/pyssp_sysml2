from __future__ import annotations

import re
from pathlib import Path

import pytest

from pyssp_sysml2.parameters import (
    has_parameter_dialect,
    mapping_specs,
    parameter_bind,
)
from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.ssv import generate_parameter_sets
from pyssp_sysml2.sysml_model import load
from tests.test_utils import COMPOSITION_NAME, write_model

REPO_ROOT = Path(__file__).resolve().parents[1]
BIND_LINE = re.compile(r"^\s*bind\s+(\S+)\s*=\s*(\S+?)\s*;")


def _model(bind_line: str, *, parts: str = "part comp : Comp;") -> str:
    return f"""
    package Orientation {{
      attribute def ParameterInterface;
      attribute def ParameterSet;

      attribute def Params :> ParameterInterface {{
        attribute count : Integer;
      }}

      attribute def Set1 :> ParameterSet {{
        attribute n = 1;
      }}

      part def Comp {{
        attribute parameters : Params;
      }}

      part def {COMPOSITION_NAME} {{
        {parts}
        attribute nominal : Set1;
        {bind_line}
      }}
    }}
    """


def _load(tmp_path: Path, bind_line: str, *, parts: str = "part comp : Comp;"):
    path = tmp_path / "model.sysml"
    write_model(path, _model(bind_line, parts=parts))
    architecture = load(path)
    return architecture, architecture.get_part_def(COMPOSITION_NAME)


def test_canonical_member_bind_resolves_by_role(tmp_path) -> None:
    """The port is on the left; the set usage is on the right."""
    _, system = _load(tmp_path, "bind comp.parameters.count = nominal.n;")

    bind = parameter_bind(system.bindings[0])

    assert bind is not None
    assert bind.port_path == ("comp",)
    assert bind.port_member == "count"
    assert bind.set_usage == "nominal"
    assert bind.set_member == "n"


def test_canonical_identity_bind_resolves_by_role(tmp_path) -> None:
    """A whole-object bind is still port-first."""
    _, system = _load(tmp_path, "bind comp.parameters = nominal;")

    bind = parameter_bind(system.bindings[0])

    assert bind is not None
    assert bind.identity
    assert bind.port_reference() == "comp.parameters"
    assert bind.set_path == ("nominal",)


def test_reversed_bind_is_rejected_with_rewrite(tmp_path) -> None:
    """Only the canonical orientation is accepted."""
    _, system = _load(tmp_path, "bind nominal.n = comp.parameters.count;")

    with pytest.raises(ValueError, match="parameter port on the left") as error:
        parameter_bind(system.bindings[0])

    assert "bind comp.parameters.count = nominal.n;" in str(error.value)


def test_port_to_port_bind_is_rejected(tmp_path) -> None:
    """Two parameter ports are a connection, not a parameter application."""
    _, system = _load(
        tmp_path,
        "bind left.parameters = right.parameters;",
        parts="part left : Comp;\n        part right : Comp;",
    )

    with pytest.raises(ValueError, match="connects two parameter ports"):
        parameter_bind(system.bindings[0])


def test_non_parameter_bind_is_ignored(tmp_path) -> None:
    """Binds without a parameter bag are ordinary SysML bindings."""
    _, system = _load(tmp_path, "bind comp.count = nominal.n;")

    assert parameter_bind(system.bindings[0]) is None


def test_generators_reject_reversed_bind(tmp_path) -> None:
    """The orientation is enforced by generators, not just the resolver."""
    architecture_dir = tmp_path / "arch"
    write_model(
        architecture_dir / "model.sysml",
        _model("bind nominal.n = comp.parameters.count;"),
    )

    with pytest.raises(ValueError, match="parameter port on the left"):
        generate_ssd(
            architecture_dir,
            tmp_path / "SystemStructure.ssd",
            COMPOSITION_NAME,
        )
    with pytest.raises(ValueError, match="parameter port on the left"):
        generate_parameter_sets(
            architecture_dir, tmp_path / "sets", COMPOSITION_NAME
        )


def _parameter_example_dirs() -> list[Path]:
    docs_examples = REPO_ROOT / "docs" / "methodology" / "examples" / "parameter-sets"
    dirs = {REPO_ROOT / "examples" / "parameter_sets"}
    dirs.update(path.parent for path in docs_examples.glob("*/model.sysml"))
    return sorted(dirs)


def test_parameter_examples_use_canonical_bind_orientation() -> None:
    """Keep the shipped examples and the library from diverging."""
    offenders: list[str] = []
    roots = (
        REPO_ROOT / "examples",
        REPO_ROOT / "docs" / "methodology" / "examples",
    )
    for path in sorted(file for root in roots for file in root.rglob("*.sysml")):
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            match = BIND_LINE.match(line)
            if match is None:
                continue
            left, right = match.groups()
            if (
                "parameters" in right.split(".")
                and "parameters" not in left.split(".")
            ):
                offenders.append(
                    f"{path.relative_to(REPO_ROOT)}:{number}: {line.strip()}"
                )

    assert not offenders, "non-canonical parameter binds:\n" + "\n".join(offenders)


def test_parameter_examples_validate() -> None:
    """Every parameter-set example parses and resolves its applications."""
    for directory in _parameter_example_dirs():
        architecture = load(directory)
        checked = 0
        for system in architecture.part_definitions.values():
            if not has_parameter_dialect(architecture, system):
                continue
            mapping_specs(architecture, system)
            checked += 1
        assert checked, (
            f"no parameter dialect found under {directory.relative_to(REPO_ROOT)}"
        )
