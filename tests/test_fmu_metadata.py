from __future__ import annotations

from pathlib import Path

import pytest
from pyssp_standard import SSD

from pyssp_sysml2.fmu_metadata import (
    FmuMetadata,
    component_source,
    fmu_metadata,
)
from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.sync import sync_sysml_from_ssd
from pyssp_sysml2.sysml import generate_sysml_from_ssd
from pyssp_sysml2.sysml_model import load
from tests.fixture_files import render_fixture
from tests.testhelpers import COMPOSITION_NAME, write_model


def _metadata_model(
    *,
    marker: str = """
      attribute def FmuMetadata {
        attribute source : String;
        attribute implementation : String;
      }
    """,
    concrete: str = """
      attribute def CompFmu :> FmuMetadata {
        attribute source = "build/fmus/Comp.fmu";
        attribute implementation = "CoSimulation";
      }
    """,
    part_body: str = "attribute fmu_meta : CompFmu;",
) -> str:
    return render_fixture(
        "fmu-metadata/template.sysml",
        marker=marker,
        concrete=concrete,
        part_body=part_body,
        COMPOSITION_NAME=COMPOSITION_NAME,
    )


def _load(tmp_path: Path, text: str):
    architecture_dir = tmp_path / "arch"
    write_model(architecture_dir / "model.sysml", text)
    return architecture_dir, load(architecture_dir)


def _component(ssd_path: Path):
    with SSD(ssd_path, mode="r") as ssd:
        assert ssd.system is not None
        [component] = ssd.system.elements
        return component


def test_fmu_metadata_resolves_concrete_and_base_values(tmp_path) -> None:
    """Concrete values override the schema; unset fields fall back to it."""
    _, architecture = _load(
        tmp_path,
        _metadata_model(
            marker="""
            attribute def FmuMetadata {
              attribute source : String;
              attribute implementation : String = "CoSimulation";
            }
            """,
            concrete="""
            attribute def CompFmu :> FmuMetadata {
              attribute source = "build/fmus/Comp.fmu";
            }
            """,
        ),
    )

    metadata = fmu_metadata(architecture, architecture.get_part_def("Comp"))

    assert metadata is not None
    assert metadata.source == "build/fmus/Comp.fmu"
    assert metadata.implementation == "CoSimulation"


def test_value_less_redeclaration_inherits_the_base_value(tmp_path) -> None:
    _, architecture = _load(
        tmp_path,
        _metadata_model(
            marker="""
            attribute def FmuMetadata {
              attribute implementation : String = "CoSimulation";
            }
            """,
            concrete="""
            attribute def CompFmu :> FmuMetadata {
              attribute implementation : String;
            }
            """,
        ),
    )

    metadata = fmu_metadata(architecture, architecture.get_part_def("Comp"))

    assert metadata is not None
    assert metadata.implementation == "CoSimulation"


def test_generate_ssd_uses_metadata_source_and_implementation(tmp_path) -> None:
    architecture_dir, _ = _load(tmp_path, _metadata_model())
    output_path = tmp_path / "SystemStructure.ssd"

    generate_ssd(architecture_dir, output_path, COMPOSITION_NAME)

    component = _component(output_path)
    assert component.source == "resources/Comp.fmu"
    assert component.implementation == "CoSimulation"


def test_component_source_is_empty_without_a_source(tmp_path) -> None:
    """A part with no authored FMU has no SSD source, whatever the metadata."""
    _, architecture = _load(
        tmp_path,
        _metadata_model(
            concrete="attribute def CompFmu :> FmuMetadata {}",
        ),
    )
    part_def = architecture.get_part_def("Comp")

    metadata = FmuMetadata(implementation="CoSimulation")
    assert component_source(part_def, None) == ""
    assert component_source(part_def, metadata) == ""
    assert component_source(part_def, fmu_metadata(architecture, part_def)) == ""


def test_metadata_is_not_emitted_as_a_parameter_connector(tmp_path) -> None:
    architecture_dir, _ = _load(
        tmp_path,
        render_fixture(
            "fmu-metadata/parameter-connector.sysml", COMPOSITION_NAME=COMPOSITION_NAME
        ),
    )
    output_path = tmp_path / "SystemStructure.ssd"

    generate_ssd(architecture_dir, output_path, COMPOSITION_NAME)

    component = _component(output_path)
    assert [(connector.name, connector.kind) for connector in component.connectors] == [
        ("gain", "parameter")
    ]


def test_metadata_on_a_system_is_rejected(tmp_path) -> None:
    architecture_dir, _ = _load(
        tmp_path,
        _metadata_model(
            part_body="""attribute fmu_meta : CompFmu;
            part inner : Inner;""",
        ).replace(
            f"part def {COMPOSITION_NAME}",
            """
            part def Inner { attribute x : Real; }
            part def """ + COMPOSITION_NAME,
        ),
    )

    with pytest.raises(ValueError, match="subparts"):
        generate_ssd(
            architecture_dir, tmp_path / "SystemStructure.ssd", COMPOSITION_NAME
        )


def test_unknown_metadata_member_is_rejected(tmp_path) -> None:
    architecture_dir, _ = _load(
        tmp_path,
        _metadata_model(
            concrete="""
            attribute def CompFmu :> FmuMetadata {
              attribute bogus = "x";
            }
            """,
        ),
    )

    with pytest.raises(ValueError, match="unsupported member"):
        generate_ssd(
            architecture_dir, tmp_path / "SystemStructure.ssd", COMPOSITION_NAME
        )


def test_non_string_metadata_value_is_rejected(tmp_path) -> None:
    architecture_dir, architecture = _load(
        tmp_path,
        _metadata_model(
            concrete="""
            attribute def CompFmu :> FmuMetadata {
              attribute implementation = 1;
            }
            """,
        ),
    )

    with pytest.raises(ValueError, match="must be a String"):
        fmu_metadata(architecture, architecture.get_part_def("Comp"))


def test_duplicate_metadata_attributes_are_rejected(tmp_path) -> None:
    architecture_dir, architecture = _load(
        tmp_path,
        _metadata_model(
            concrete="""
            attribute def CompFmu :> FmuMetadata {
              attribute implementation = "CoSimulation";
            }
            attribute def OtherFmu :> FmuMetadata {
              attribute implementation = "ModelExchange";
            }
            """,
            part_body="""attribute fmu_meta : CompFmu;
            attribute other : OtherFmu;""",
        ),
    )

    with pytest.raises(ValueError, match="multiple FMU metadata"):
        fmu_metadata(architecture, architecture.get_part_def("Comp"))


def test_metadata_marker_cannot_be_used_directly(tmp_path) -> None:
    architecture_dir, architecture = _load(
        tmp_path,
        _metadata_model(part_body="attribute fmu_meta : FmuMetadata;"),
    )

    with pytest.raises(ValueError, match="schema directly"):
        fmu_metadata(architecture, architecture.get_part_def("Comp"))


def test_missing_metadata_marker_is_rejected(tmp_path) -> None:
    architecture_dir, architecture = _load(
        tmp_path,
        _metadata_model(
            marker="",
        ),
    )

    with pytest.raises(ValueError, match="missing marker definition"):
        fmu_metadata(architecture, architecture.get_part_def("Comp"))


def test_unmarked_metadata_usage_is_rejected(tmp_path) -> None:
    architecture_dir, _ = _load(
        tmp_path,
        _metadata_model(
            concrete="attribute def CompFmu { attribute implementation = \"CoSimulation\"; }",
        ),
    )

    with pytest.raises(ValueError, match="marked ':> FmuMetadata'"):
        generate_ssd(
            architecture_dir, tmp_path / "SystemStructure.ssd", COMPOSITION_NAME
        )


def test_sync_updates_implementation_and_preserves_source(tmp_path) -> None:
    _load(tmp_path, _metadata_model())
    architecture_dir = tmp_path / "arch"
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(architecture_dir, ssd_path, COMPOSITION_NAME)

    with SSD(ssd_path, mode="a") as ssd:
        assert ssd.system is not None
        [component] = ssd.system.elements
        component.implementation = "ModelExchange"

    synced_dir = tmp_path / "synced"
    sync_sysml_from_ssd(
        architecture_dir,
        ssd_path,
        COMPOSITION_NAME,
        output_architecture_dir=synced_dir,
    )

    synced = load(synced_dir)
    metadata = fmu_metadata(synced, synced.get_part_def("Comp"))
    assert metadata is not None
    assert metadata.source == "build/fmus/Comp.fmu"
    assert metadata.implementation == "ModelExchange"


def test_sync_resolves_empty_component_source_by_part_name(tmp_path) -> None:
    """An empty SSD source carries no FMU and preserves the authored source."""
    _load(tmp_path, _metadata_model())
    architecture_dir = tmp_path / "arch"
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(architecture_dir, ssd_path, COMPOSITION_NAME)

    with SSD(ssd_path, mode="a") as ssd:
        assert ssd.system is not None
        [component] = ssd.system.elements
        component.source = ""

    synced_dir = tmp_path / "synced"
    sync_sysml_from_ssd(
        architecture_dir,
        ssd_path,
        COMPOSITION_NAME,
        output_architecture_dir=synced_dir,
    )

    synced = load(synced_dir)
    metadata = fmu_metadata(synced, synced.get_part_def("Comp"))
    assert metadata is not None
    assert metadata.source == "build/fmus/Comp.fmu"


def test_retired_implementation_attribute_is_rejected(tmp_path) -> None:
    architecture_dir = tmp_path / "arch"
    write_model(
        architecture_dir / "model.sysml",
        render_fixture(
            "fmu-metadata/retired-implementation.sysml",
            COMPOSITION_NAME=COMPOSITION_NAME,
        ),
    )

    with pytest.raises(
        ValueError, match="pyssp_implementation is no longer supported"
    ):
        generate_ssd(
            architecture_dir, tmp_path / "SystemStructure.ssd", COMPOSITION_NAME
        )


def test_sysml_roundtrip_preserves_implementation_without_source(tmp_path) -> None:
    """SSD source is authoring data: recovery keeps the name and implementation."""
    ssd_path = tmp_path / "source.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        top = ssd.new_system(COMPOSITION_NAME)
        ssd.rename(COMPOSITION_NAME)
        top.add_component(
            "comp",
            source="resources/Renamed.fmu",
            implementation="CoSimulation",
        )

    architecture_dir = tmp_path / "recovered"
    architecture_dir.mkdir()
    generated = architecture_dir / "architecture.sysml"
    generate_sysml_from_ssd(ssd_path, generated, COMPOSITION_NAME)

    text = generated.read_text()
    assert "attribute def FmuMetadata {" in text
    assert "attribute def RenamedFmuMetadata :> FmuMetadata {" in text
    assert 'attribute implementation : String = "CoSimulation";' in text
    assert "attribute fmu_meta : RenamedFmuMetadata;" in text

    regenerated = tmp_path / "regenerated.ssd"
    generate_ssd(architecture_dir, regenerated, COMPOSITION_NAME)
    component = _component(regenerated)
    assert component.source == ""
    assert component.implementation == "CoSimulation"
