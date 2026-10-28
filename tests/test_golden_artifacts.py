"""Committed conversion goldens, checked by an independent validator.

Each case is a small SysML architecture plus the artifacts generated from it.
The generator is run into ``tmp_path``; every produced byte is compared with the
committed golden, and every produced document is re-validated through the
``pyssp_standard`` facade (XSD plus semantic checks), so the writer and the
checker are different implementations.

Regenerate with ``UPDATE_GOLDENS=1`` and review the diff; never in CI.
See ``README.md`` in this directory.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from difflib import unified_diff
from pathlib import Path

import pytest
from pyssp_standard import ModelDescription, SSD, SSM, SSV

from pyssp_sysml2.fmi import generate_model_descriptions
from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.ssm import generate_parameter_mappings
from pyssp_sysml2.ssv import generate_parameter_sets

GOLDEN_ROOT = Path(__file__).resolve().parent / "golden"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESOURCES = Path(__file__).resolve().parent / "resources"

#: Case directory -> composition to generate.
CASES = {
    "identity": "IdentityComposition",
    "mapping": "MappingComposition",
}

#: Fixture files that are inputs, not goldens.
INPUTS = {"architecture.sysml"}

#: Frozen ``generationDateAndTime`` shared by every golden model description.
GENERATION_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)

UPDATE_GOLDENS = os.environ.get("UPDATE_GOLDENS") == "1"


def _generate(case_dir: Path, composition: str, output_dir: Path) -> None:
    generate_ssd(case_dir, output_dir / "SystemStructure.ssd", composition)
    generate_parameter_sets(
        case_dir, output_dir / "parameter_sets", composition
    )
    generate_parameter_mappings(case_dir, output_dir, composition)
    generate_model_descriptions(
        case_dir,
        output_dir,
        composition,
        generation_time=GENERATION_TIME,
    )


def _files(root: Path, *, exclude: set[str] = frozenset()) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name not in exclude
    }


def _validate(path: Path) -> None:
    """Re-parse and check one artifact through the ``pyssp_standard`` facade."""
    if path.name == "modelDescription.xml":
        facade = ModelDescription
    else:
        facade = {".ssd": SSD, ".ssv": SSV, ".ssm": SSM}[path.suffix]
    with facade(path, mode="r") as document:
        document.check_compliance()


def _assert_same_bytes(committed: Path, generated: Path) -> None:
    committed_bytes = committed.read_bytes()
    generated_bytes = generated.read_bytes()
    if committed_bytes == generated_bytes:
        return
    diff = "".join(
        unified_diff(
            committed_bytes.decode("utf-8").splitlines(keepends=True),
            generated_bytes.decode("utf-8").splitlines(keepends=True),
            fromfile=f"committed/{committed.name}",
            tofile=f"generated/{generated.name}",
        )
    )
    pytest.fail(
        f"{committed.relative_to(PROJECT_ROOT)} does not match generation:\n{diff}"
    )


@pytest.mark.parametrize("case", sorted(CASES))
def test_golden_artifacts_are_reproducible_and_valid(
    case: str, tmp_path: Path
) -> None:
    """Generation reproduces the committed bytes and the facade accepts them."""
    case_dir = GOLDEN_ROOT / case
    output_dir = tmp_path / "generated"

    _generate(case_dir, CASES[case], output_dir)

    generated = _files(output_dir)
    if UPDATE_GOLDENS:
        committed_before = _files(case_dir, exclude=INPUTS)
        for relative, path in generated.items():
            destination = case_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(path.read_bytes())
        for relative in sorted(set(committed_before) - set(generated)):
            stale = case_dir / relative
            stale.unlink()
            if not any(stale.parent.iterdir()):
                stale.parent.rmdir()

    committed = _files(case_dir, exclude=INPUTS)
    assert sorted(generated) == sorted(committed), (
        f"{case}: produced {sorted(generated)} but goldens are {sorted(committed)}; "
        "run with UPDATE_GOLDENS=1 and review the result"
    )
    for relative in sorted(generated):
        _validate(generated[relative])
        _assert_same_bytes(case_dir / relative, generated[relative])


@pytest.mark.parametrize("name", ["openscaling"])
def test_vendored_ssd_fixtures_pass_the_facade_validator(name: str) -> None:
    """Externally authored SSD fixtures are readable and XSD compliant."""
    with SSD(RESOURCES / f"{name}.ssd", mode="r") as ssd:
        ssd.check_compliance()
        system = ssd.system
        assert system is not None
        assert system.elements
