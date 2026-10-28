from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from pyssp_sysml2.artifacts import fmi
from pyssp_sysml2.artifacts.fmi import generate_model_descriptions
from tests.fixture_files import fixture_text, render_fixture
from tests.testhelpers import COMPOSITION_NAME, write_model

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: Frozen generation time used by the determinism tests.
FROZEN_TIME = datetime(2026, 10, 28, 12, 34, 56, tzinfo=timezone.utc)

#: ``uuid5`` of ``pyssp_sysml2/<composition>/<component>`` in ``NAMESPACE_URL``.
#: Pinned literally so a namespace or input-format change cannot pass silently.
EXPECTED_GUID = "85376515-ccc2-5b66-b935-bc5b1d5cbb01"


def _write_status_component(root: Path) -> Path:
    """A composition with one leaf component exposing a single output port."""
    write_model(
        root / "model.sysml",
        render_fixture(
            "generate-model-descriptions/status-component.sysml",
            COMPOSITION_NAME=COMPOSITION_NAME,
        ),
    )
    return root


def _model_description_summary(path) -> list[str]:
    root = ET.parse(path).getroot()
    scalar_variables = [
        elem
        for elem in root.findall(".//ScalarVariable")
        if elem.get("name") is not None
    ]
    outputs = {
        int(elem.get("index"))
        for elem in root.findall("./ModelStructure/Outputs/Unknown")
        if elem.get("index") is not None
    }

    lines = [f"generationTool:{root.get('generationTool')}"]
    for index, variable in enumerate(scalar_variables, start=1):
        type_elem = next(iter(variable), None)
        assert type_elem is not None
        tag = type_elem.tag.split("}", 1)[-1]
        start = type_elem.get("start")
        output_flag = "output" if index in outputs else "nonoutput"
        lines.append(
            f"{variable.get('name')}|{variable.get('causality')}|"
            f"{variable.get('variability')}|{tag}|{start}|{variable.get('valueReference')}|{output_flag}"
        )
    return lines


def test_generate_model_descriptions_from_small_snippet(tmp_path) -> None:
    """Model description export preserves expected FMI variables and output markers."""
    architecture_dir = tmp_path / "arch"
    architecture_dir.mkdir(parents=True, exist_ok=True)

    write_model(
        architecture_dir / "ports.sysml",
        fixture_text("generate-model-descriptions/ports.sysml"),
    )

    write_model(
        architecture_dir / "parts.sysml",
        render_fixture(
            "generate-model-descriptions/parts.sysml", COMPOSITION_NAME=COMPOSITION_NAME
        ),
    )

    output_dir = tmp_path / "model_descriptions"

    written = generate_model_descriptions(
        architecture_path=architecture_dir,
        output_dir=output_dir,
        composition=COMPOSITION_NAME,
    )

    assert len(written) == 1

    a_path = output_dir / "Comp" / "modelDescription.xml"
    assert a_path in written

    assert _model_description_summary(a_path) == [
        "generationTool:pyssp_sysml2 tooling",
        "int_list[0]|parameter|fixed|Integer|1|0|nonoutput",
        "int_list[1]|parameter|fixed|Integer|2|1|nonoutput",
        "bool_list[0]|parameter|fixed|Boolean|true|2|nonoutput",
        "bool_list[1]|parameter|fixed|Boolean|false|3|nonoutput",
        "status.ok|output|None|Boolean|None|4|output",
    ]


def test_generate_model_descriptions_rejects_flat_parameters(tmp_path: Path) -> None:
    write_model(
        tmp_path / "arch" / "model.sysml",
        render_fixture(
            "generate-model-descriptions/flat-parameters.sysml",
            COMPOSITION_NAME=COMPOSITION_NAME,
        ),
    )

    with pytest.raises(ValueError, match="flat parameter attribute"):
        generate_model_descriptions(
            tmp_path / "arch", tmp_path / "model_descriptions", COMPOSITION_NAME
        )


def test_generate_model_descriptions_writes_expected_root_metadata(tmp_path: Path) -> None:
    """Generated FMI metadata includes stable identifiers and output model structure."""
    write_model(
        tmp_path / "arch" / "model.sysml",
        render_fixture(
            "generate-model-descriptions/status-component.sysml",
            COMPOSITION_NAME=COMPOSITION_NAME,
        ),
    )

    output_dir = tmp_path / "model_descriptions"
    [written] = generate_model_descriptions(tmp_path / "arch", output_dir, COMPOSITION_NAME)

    root = ET.parse(written).getroot()
    assert root.tag == "fmiModelDescription"
    assert root.get("modelName") == f"{COMPOSITION_NAME}.Comp"
    assert root.get("guid", "").startswith("{")
    assert root.get("guid", "").endswith("}")
    assert root.get("variableNamingConvention") == "structured"

    co_sim = root.find("./CoSimulation")
    assert co_sim is not None
    assert co_sim.get("modelIdentifier") == "Comp"

    outputs = root.findall("./ModelStructure/Outputs/Unknown")
    initial_unknowns = root.findall("./ModelStructure/InitialUnknowns/Unknown")
    assert [elem.get("index") for elem in outputs] == ["1"]
    assert [elem.get("index") for elem in initial_unknowns] == ["1"]


def test_generate_model_descriptions_writes_one_file_per_component_type(tmp_path: Path) -> None:
    """Each referenced part definition gets its own model description output."""
    write_model(
        tmp_path / "arch" / "model.sysml",
        render_fixture(
            "generate-model-descriptions/two-components.sysml",
            COMPOSITION_NAME=COMPOSITION_NAME,
        ),
    )

    output_dir = tmp_path / "model_descriptions"
    written = generate_model_descriptions(tmp_path / "arch", output_dir, COMPOSITION_NAME)

    assert sorted(path.relative_to(output_dir).as_posix() for path in written) == [
        "Controller/modelDescription.xml",
        "Sensor/modelDescription.xml",
    ]


def test_two_generations_with_a_fixed_clock_are_byte_identical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fixed generation time makes the whole artifact reproducible.

    The ambient clock is moved between the two runs, so a generator that fell
    back to ``utc_now`` would differ even within the same second.
    """
    architecture_dir = _write_status_component(tmp_path / "arch")

    first = generate_model_descriptions(
        architecture_dir,
        tmp_path / "first",
        COMPOSITION_NAME,
        generation_time=FROZEN_TIME,
    )
    monkeypatch.setattr(fmi, "utc_now", lambda: FROZEN_TIME + timedelta(days=1))
    second = generate_model_descriptions(
        architecture_dir,
        tmp_path / "second",
        COMPOSITION_NAME,
        generation_time=FROZEN_TIME,
    )

    assert len(first) == len(second) == 1
    assert first[0].read_bytes() == second[0].read_bytes()
    assert _generation_timestamp(second[0]) == "2026-10-28T12:34:56Z"


def test_generation_time_comes_from_the_clock_hook_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``utc_now`` is the injectable default source of generation time."""
    architecture_dir = _write_status_component(tmp_path / "arch")
    times = iter([FROZEN_TIME, FROZEN_TIME + timedelta(hours=1)])
    monkeypatch.setattr(fmi, "utc_now", lambda: next(times))

    [first] = generate_model_descriptions(
        architecture_dir, tmp_path / "first", COMPOSITION_NAME
    )
    [second] = generate_model_descriptions(
        architecture_dir, tmp_path / "second", COMPOSITION_NAME
    )

    assert _generation_timestamp(first) == "2026-10-28T12:34:56Z"
    assert _generation_timestamp(second) == "2026-10-28T13:34:56Z"


def test_the_default_clock_is_timezone_aware_utc() -> None:
    """The documented default is the current UTC time, never a naive local one."""
    moment = fmi.utc_now()

    assert moment.tzinfo is not None
    assert moment.utcoffset() == timedelta(0)
    assert fmi.format_generation_timestamp(moment).endswith("Z")


def test_a_naive_generation_time_is_rejected() -> None:
    """A naive timestamp would silently mean local time, so it is an error."""
    with pytest.raises(ValueError, match="timezone-aware"):
        fmi.format_generation_timestamp(datetime(2026, 10, 28, 12, 0, 0))


def test_model_description_pins_fmi_version_and_guid_namespace(tmp_path: Path) -> None:
    """The FMI version and guid derivation are part of the artifact contract."""
    architecture_dir = _write_status_component(tmp_path / "arch")

    [written] = generate_model_descriptions(
        architecture_dir,
        tmp_path / "out",
        COMPOSITION_NAME,
        generation_time=FROZEN_TIME,
    )

    root = ET.parse(written).getroot()
    assert root.get("fmiVersion") == "2.0"
    assert fmi.FMI_VERSION == "2.0"
    assert root.get("guid") == "{" + EXPECTED_GUID + "}"
    assert root.get("numberOfEventIndicators") == "0"
    assert root.get("generationDateAndTime") == "2026-10-28T12:34:56Z"


def test_generation_does_not_write_into_the_checkout(tmp_path: Path) -> None:
    """Generated files land only below ``output_dir``, never beside the package."""
    architecture_dir = _write_status_component(tmp_path / "arch")
    before = _tree_snapshot(PROJECT_ROOT)

    generate_model_descriptions(
        architecture_dir, tmp_path / "out", COMPOSITION_NAME
    )

    assert _tree_snapshot(PROJECT_ROOT) == before
    assert not (PROJECT_ROOT / "build" / "fmu_pre").exists()


def _generation_timestamp(path: Path) -> str:
    return ET.parse(path).getroot().get("generationDateAndTime", "")


#: Directories whose contents are not this package's source tree.
_SNAPSHOT_SKIP = {"__pycache__", ".pytest_cache", ".git", "3rd_party"}


def _tree_snapshot(root: Path) -> dict[str, str]:
    """Path -> state for every file and directory in the source tree.

    Files carry their size, mtime, and content digest; directories their mtime,
    so creating an empty directory is still a visible change.
    """
    snapshot: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if _SNAPSHOT_SKIP.intersection(relative.parts):
            continue
        stat = path.stat()
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            snapshot[relative.as_posix()] = (
                f"file:{stat.st_mtime_ns}:{stat.st_size}:{digest}"
            )
        else:
            snapshot[relative.as_posix()] = f"dir:{stat.st_mtime_ns}"
    return snapshot
