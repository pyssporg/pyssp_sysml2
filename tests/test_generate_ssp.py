from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest
from pyssp_standard import FMU, SSP, SSV

from pyssp_sysml2.cli import main
from pyssp_sysml2.fmi import generate_model_descriptions
from pyssp_sysml2.ssp import generate_ssp
from tests.test_utils import COMPOSITION_NAME, write_model


def _write_architecture(
    root: Path,
    *,
    source: str | None,
    implementation: str | None = "CoSimulation",
    parameterized: bool = True,
    flat_connector: bool = False,
) -> Path:
    fields = []
    if source is not None:
        fields.append(f'attribute source = "{source}";')
    if implementation is not None:
        fields.append(f'attribute implementation = "{implementation}";')
    metadata_fields = "\n    ".join(fields)

    parameter_defs = ""
    parameter_port = ""
    composition_parameters = ""
    if parameterized:
        parameter_defs = """
          port def ParameterInterface;
          attribute def ParameterSet;

          port def CompParameters :> ParameterInterface {
            attribute gain : Real;
          }

          attribute def NominalSet :> ParameterSet {
            attribute gain = 2.0;
          }
        """
        parameter_port = "in port parameters : CompParameters;"
        composition_parameters = """
            attribute nominal : NominalSet;
            bind comp.parameters.gain = nominal.gain;
        """

    write_model(
        root / "model.sysml",
        f"""
        package Example {{
          {parameter_defs}

          attribute def FmuMetadata {{
            attribute source : String;
            attribute implementation : String;
          }}

          attribute def CompFmu :> FmuMetadata {{
            {metadata_fields}
          }}

          port def Signal {{
            attribute y : Real;
            {"attribute pyssp_flat_connector : Boolean = true;" if flat_connector else ""}
          }}

          part def Comp {{
            attribute fmu_meta : CompFmu;
            {parameter_port}
            out port output : Signal;
          }}

          part def {COMPOSITION_NAME} {{
            part comp : Comp;
            {composition_parameters}
          }}
        }}
        """,
    )
    return root


def _build_fmu(
    architecture_dir: Path, fmu_path: Path, *, part_name: str = "Comp"
) -> Path:
    model_description_dir = fmu_path.parent / "model_descriptions"
    generate_model_descriptions(
        architecture_dir, model_description_dir, COMPOSITION_NAME
    )
    FMU.create(
        fmu_path,
        model_description=model_description_dir
        / part_name
        / "modelDescription.xml",
    )
    return fmu_path


def _write_mismatched_fmu(fmu_path: Path) -> Path:
    model_description = """<?xml version="1.0" encoding="UTF-8"?>
<fmiModelDescription xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" fmiVersion="2.0" modelName="Comp" guid="{00000000-0000-0000-0000-000000000001}" generationTool="test" variableNamingConvention="structured">
  <CoSimulation modelIdentifier="Comp" canHandleVariableCommunicationStepSize="true"/>
  <ModelVariables>
    <ScalarVariable name="other" valueReference="0" causality="output">
      <Real/>
    </ScalarVariable>
  </ModelVariables>
  <ModelStructure>
    <Outputs>
      <Unknown index="1"/>
    </Outputs>
  </ModelStructure>
</fmiModelDescription>
"""
    with zipfile.ZipFile(fmu_path, "w") as archive:
        archive.writestr("modelDescription.xml", model_description)
    return fmu_path


def _component(ssp_path: Path):
    with SSP(ssp_path, mode="r") as ssp:
        with ssp.system_structure() as ssd:
            assert ssd.xml.system is not None
            return next(
                element
                for element in ssd.xml.system.elements
                if element.name == "comp"
            )


def test_generate_ssp_packages_ssd_fmu_and_parameter_set(tmp_path: Path) -> None:
    """The archive contains the SSD, the built FMU, and the applied SSV."""
    architecture_dir = _write_architecture(
        tmp_path / "arch", source=str(tmp_path / "Comp.fmu")
    )
    _build_fmu(architecture_dir, tmp_path / "Comp.fmu")
    output_path = tmp_path / "model.ssp"

    generate_ssp(architecture_dir, output_path, COMPOSITION_NAME)

    with zipfile.ZipFile(output_path, "r") as archive:
        assert set(archive.namelist()) == {
            "SystemStructure.ssd",
            "resources/Comp.fmu",
            "resources/parameter_sets/NominalSet.ssv",
        }

    component = _component(output_path)
    assert component.source == "resources/Comp.fmu"
    assert component.implementation == "CoSimulation"

    with SSP(output_path, mode="r") as ssp:
        assert ssp.resources == ["Comp.fmu", "parameter_sets/NominalSet.ssv"]
        with ssp.system_structure() as ssd:
            assert ssd.xml.system is not None
            [binding] = ssd.xml.system.parameter_bindings
            assert binding.source == "resources/parameter_sets/NominalSet.ssv"

        ssv_path = ssp.runtime.resolve(
            "resources/parameter_sets/NominalSet.ssv"
        )
        with SSV(ssv_path, mode="r") as ssv:
            [parameter] = ssv.xml.parameters
            assert parameter.name == "gain"
            assert parameter.attributes["value"] == "2"


def test_generate_ssp_rejects_unsafe_parameter_set_prefix(tmp_path: Path) -> None:
    architecture_dir = _write_architecture(
        tmp_path / "arch", source=str(tmp_path / "Comp.fmu")
    )

    with pytest.raises(ValueError, match="without '\\.\\.'"):
        generate_ssp(
            architecture_dir,
            tmp_path / "model.ssp",
            COMPOSITION_NAME,
            parameter_set_prefix="../outside",
        )


def test_generate_ssp_uses_custom_parameter_set_prefix(tmp_path: Path) -> None:
    architecture_dir = _write_architecture(
        tmp_path / "arch", source=str(tmp_path / "Comp.fmu")
    )
    _build_fmu(architecture_dir, tmp_path / "Comp.fmu")
    output_path = tmp_path / "model.ssp"

    generate_ssp(
        architecture_dir,
        output_path,
        COMPOSITION_NAME,
        parameter_set_prefix="custom_sets",
    )

    with zipfile.ZipFile(output_path, "r") as archive:
        assert "custom_sets/NominalSet.ssv" in archive.namelist()

    with SSP(output_path, mode="r") as ssp:
        with ssp.system_structure() as ssd:
            assert ssd.xml.system is not None
            [binding] = ssd.xml.system.parameter_bindings
            assert binding.source == "custom_sets/NominalSet.ssv"


def test_generate_ssp_without_parameter_sets(tmp_path: Path) -> None:
    architecture_dir = _write_architecture(
        tmp_path / "arch",
        source=str(tmp_path / "Comp.fmu"),
        parameterized=False,
    )
    _build_fmu(architecture_dir, tmp_path / "Comp.fmu")
    output_path = tmp_path / "model.ssp"

    generate_ssp(architecture_dir, output_path, COMPOSITION_NAME)

    with zipfile.ZipFile(output_path, "r") as archive:
        assert set(archive.namelist()) == {
            "SystemStructure.ssd",
            "resources/Comp.fmu",
        }

    with SSP(output_path, mode="r") as ssp:
        with ssp.system_structure() as ssd:
            assert ssd.xml.system is not None
            assert ssd.xml.system.parameter_bindings == []


def test_generate_ssp_rejects_missing_fmu_file(tmp_path: Path) -> None:
    architecture_dir = _write_architecture(
        tmp_path / "arch", source=str(tmp_path / "Missing.fmu")
    )

    with pytest.raises(FileNotFoundError, match="does not exist"):
        generate_ssp(
            architecture_dir, tmp_path / "model.ssp", COMPOSITION_NAME
        )


def test_generate_ssp_rejects_connector_name_mismatch(tmp_path: Path) -> None:
    architecture_dir = _write_architecture(
        tmp_path / "arch", source=str(tmp_path / "Comp.fmu")
    )
    _write_mismatched_fmu(tmp_path / "Comp.fmu")

    with pytest.raises(ValueError, match="missing variable"):
        generate_ssp(
            architecture_dir, tmp_path / "model.ssp", COMPOSITION_NAME
        )


def test_generate_ssp_validates_ssd_connector_names(tmp_path: Path) -> None:
    architecture_dir = _write_architecture(
        tmp_path / "arch",
        source=str(tmp_path / "Comp.fmu"),
        flat_connector=True,
    )
    _build_fmu(architecture_dir, tmp_path / "Comp.fmu")

    with pytest.raises(ValueError, match="missing variable.*output"):
        generate_ssp(
            architecture_dir, tmp_path / "model.ssp", COMPOSITION_NAME
        )


def test_generate_ssp_can_skip_fmu_validation(tmp_path: Path) -> None:
    architecture_dir = _write_architecture(
        tmp_path / "arch", source=str(tmp_path / "Comp.fmu")
    )
    _write_mismatched_fmu(tmp_path / "Comp.fmu")
    output_path = tmp_path / "model.ssp"

    generate_ssp(
        architecture_dir,
        output_path,
        COMPOSITION_NAME,
        validate_fmus=False,
    )

    assert _component(output_path).source == "resources/Comp.fmu"


def test_generate_ssp_rejects_implementation_mismatch(tmp_path: Path) -> None:
    architecture_dir = _write_architecture(
        tmp_path / "arch",
        source=str(tmp_path / "Comp.fmu"),
        implementation="ModelExchange",
    )
    _build_fmu(architecture_dir, tmp_path / "Comp.fmu")

    with pytest.raises(ValueError, match="exposes 'CoSimulation'"):
        generate_ssp(
            architecture_dir, tmp_path / "model.ssp", COMPOSITION_NAME
        )


def test_generate_ssp_packages_extracted_fmu_directory(tmp_path: Path) -> None:
    architecture_dir = _write_architecture(
        tmp_path / "arch",
        source=str(tmp_path / "extracted"),
    )
    model_description_dir = tmp_path / "model_descriptions"
    generate_model_descriptions(
        architecture_dir, model_description_dir, COMPOSITION_NAME
    )
    fmu_dir = tmp_path / "extracted"
    fmu_dir.mkdir()
    shutil.copy2(
        model_description_dir / "Comp" / "modelDescription.xml",
        fmu_dir / "modelDescription.xml",
    )
    output_path = tmp_path / "model.ssp"

    generate_ssp(architecture_dir, output_path, COMPOSITION_NAME)

    with zipfile.ZipFile(output_path, "r") as archive:
        assert "resources/Comp.fmu" in archive.namelist()

    with SSP(output_path, mode="r") as ssp:
        assert "Comp.fmu" in ssp.resources
        assert ssp.runtime.resolve("resources/Comp.fmu").is_file()


def test_generate_ssp_packages_nested_component(tmp_path: Path) -> None:
    architecture_dir = tmp_path / "arch"
    write_model(
        architecture_dir / "model.sysml",
        f"""
        package Example {{
          attribute def FmuMetadata {{
            attribute source : String;
            attribute implementation : String;
          }}

          attribute def LeafFmu :> FmuMetadata {{
            attribute source = "{tmp_path / 'Leaf.fmu'}";
            attribute implementation = "CoSimulation";
          }}

          port def Signal {{
            attribute y : Real;
          }}

          part def Leaf {{
            attribute fmu_meta : LeafFmu;
            out port output : Signal;
          }}

          part def Sub {{
            part leaf : Leaf;
          }}

          part def {COMPOSITION_NAME} {{
            part sub : Sub;
          }}
        }}
        """,
    )
    _build_fmu(architecture_dir, tmp_path / "Leaf.fmu", part_name="Leaf")
    output_path = tmp_path / "model.ssp"

    generate_ssp(architecture_dir, output_path, COMPOSITION_NAME)

    with SSP(output_path, mode="r") as ssp:
        with ssp.system_structure() as ssd:
            assert ssd.xml.system is not None
            [sub] = ssd.xml.system.elements
            [leaf] = sub.elements
            assert leaf.name == "leaf"
            assert leaf.source == "resources/Leaf.fmu"


def test_pyssp_generate_ssp_cli(tmp_path: Path) -> None:
    architecture_dir = _write_architecture(
        tmp_path / "arch", source="Comp.fmu"
    )
    _build_fmu(architecture_dir, tmp_path / "Comp.fmu")
    output_path = tmp_path / "model.ssp"

    code = main(
        [
            "generate",
            "ssp",
            "--architecture",
            str(architecture_dir),
            "--composition",
            COMPOSITION_NAME,
            "--output",
            str(output_path),
            "--fmu-root",
            str(tmp_path),
        ]
    )

    assert code == 0
    assert output_path.exists()
    assert _component(output_path).source == "resources/Comp.fmu"


def test_generate_ssp_exports_design_without_fmu_source(tmp_path: Path) -> None:
    """A part without fmu_meta.source needs no flag and gets an empty source."""
    architecture_dir = _write_architecture(tmp_path / "arch", source=None)
    output_path = tmp_path / "model.ssp"

    with pytest.warns(UserWarning, match="Comp: FMU source is missing"):
        generate_ssp(architecture_dir, output_path, COMPOSITION_NAME)

    with zipfile.ZipFile(output_path, "r") as archive:
        assert set(archive.namelist()) == {
            "SystemStructure.ssd",
            "resources/parameter_sets/NominalSet.ssv",
        }

    component = _component(output_path)
    assert component.source == ""
    assert component.implementation == "CoSimulation"


def test_generate_ssp_allows_missing_fmu_file(tmp_path: Path) -> None:
    architecture_dir = _write_architecture(
        tmp_path / "arch", source=str(tmp_path / "Missing.fmu")
    )
    output_path = tmp_path / "model.ssp"

    with pytest.warns(UserWarning, match="FMU source is missing"):
        generate_ssp(
            architecture_dir,
            output_path,
            COMPOSITION_NAME,
            allow_missing_fmus=True,
        )

    with zipfile.ZipFile(output_path, "r") as archive:
        assert "resources/Comp.fmu" not in archive.namelist()

    assert _component(output_path).source == "resources/Comp.fmu"


def test_generate_ssp_still_validates_present_fmus_in_design_mode(
    tmp_path: Path,
) -> None:
    architecture_dir = _write_architecture(
        tmp_path / "arch", source=str(tmp_path / "Comp.fmu")
    )
    _write_mismatched_fmu(tmp_path / "Comp.fmu")

    with pytest.raises(ValueError, match="missing variable"):
        generate_ssp(
            architecture_dir,
            tmp_path / "model.ssp",
            COMPOSITION_NAME,
            allow_missing_fmus=True,
        )
