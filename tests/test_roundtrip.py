"""Regression tests for SSD -> SysML -> SSD fidelity."""

from __future__ import annotations

from pathlib import Path

from pyssp_standard.ssd import (
    Component,
    Connector,
    DefaultExperiment,
    ParameterBinding,
    SSD,
    System,
)

from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.ssv import generate_parameter_sets
from pyssp_sysml2.sysml import generate_sysml_from_ssd
from tests.test_utils import write_model


def _write_reference_ssp(root: Path) -> Path:
    root.mkdir(parents=True)
    parameter_path = root / "parameters.ssv"
    parameter_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<ssv:ParameterSet xmlns:ssv="http://ssp-standard.org/SSP1/SystemStructureParameterValues" version="1.0" name="parameters">
  <ssv:Parameters>
    <ssv:Parameter name="gain.k">
      <ssv:Real value="3.0" />
    </ssv:Parameter>
  </ssv:Parameters>
</ssv:ParameterSet>
"""
    )

    ssd_path = root / "SystemStructure.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        ssd.xml.name = "RoundTrip"
        ssd.xml.version = "1.0"
        ssd.xml.system = System(name="RoundTrip")
        ssd.xml.system.parameter_bindings = [ParameterBinding(source="parameters.ssv")]

        gain = Component()
        gain.name = "gain"
        gain.source = "resources/Gain.fmu"
        gain.implementation = "CoSimulation"
        gain.connectors.extend(
            [
                Connector(name="k", kind="parameter", type_name="Real"),
                Connector(name="u", kind="input", type_name="Real"),
                Connector(name="y", kind="output", type_name="Real"),
            ]
        )
        ssd.xml.system.elements.append(gain)

        experiment = DefaultExperiment()
        experiment.start_time = 0.0
        experiment.stop_time = 2.0
        ssd.xml.default_experiment = experiment
    return ssd_path


def test_ssd_sysml_ssd_preserves_metadata(tmp_path: Path) -> None:
    ssd_path = _write_reference_ssp(tmp_path / "source")
    architecture_dir = tmp_path / "architecture"
    architecture_dir.mkdir()
    generated = architecture_dir / "architecture.sysml"
    generate_sysml_from_ssd(ssd_path, generated)

    generated_text = generated.read_text()
    assert "attribute def GainParameters :> ParameterInterface" in generated_text
    assert "attribute def parameters :> ParameterSet" in generated_text
    assert "attribute parameters_set : parameters;" in generated_text
    assert "bind parameters_set = gain.parameters;" in generated_text

    regenerated = tmp_path / "regenerated.ssd"
    generate_ssd(architecture_dir, regenerated, "RoundTrip")

    with SSD(regenerated, mode="r") as ssd:
        assert ssd.xml.default_experiment.start_time == 0.0
        assert ssd.xml.default_experiment.stop_time == 2.0
        [binding] = ssd.xml.system.parameter_bindings
        assert binding.source == "parameter_sets/parameters.ssv"
        assert binding.prefix == "gain"
        assert binding.parameter_mapping is None

        component = ssd.xml.system.elements[0]
        assert component.name == "gain"
        assert component.implementation == "CoSimulation"
        connectors = {connector.name: connector.kind for connector in component.connectors}
        assert connectors == {"k": "parameter", "u": "input", "y": "output"}


def test_sysml_ssd_sysml_ssd_preserves_explicit_parameter_mapping(
    tmp_path: Path,
) -> None:
    """A SysML->SSD->SysML->SSD loop keeps parameter mapping semantics."""
    architecture_dir = tmp_path / "source_arch"
    write_model(
        architecture_dir / "model.sysml",
        """
        package Example {
          attribute def ParameterInterface;
          attribute def ParameterSet;

          attribute def Params :> ParameterInterface {
            attribute count : Integer;
            attribute xs : Real[2];
          }

          attribute def Nom :> ParameterSet {
            attribute n = 5;
            attribute x = (1.0, 2.0);
          }

          part def Comp {
            attribute parameters : Params;
          }

          part def SystemComposition {
            part c : Comp;
            attribute nominal : Nom;
            bind nominal.n = c.parameters.count;
            bind nominal.x = c.parameters.xs;
          }
        }
        """,
    )

    first_ssd = tmp_path / "source" / "SystemStructure.ssd"
    generate_ssd(architecture_dir, first_ssd, "SystemComposition")
    generate_parameter_sets(
        architecture_dir,
        first_ssd.parent / "parameter_sets",
        "SystemComposition",
    )

    roundtrip_arch = tmp_path / "roundtrip_arch"
    roundtrip_arch.mkdir()
    generate_sysml_from_ssd(first_ssd, roundtrip_arch / "architecture.sysml")

    second_ssd = tmp_path / "regenerated.ssd"
    generate_ssd(roundtrip_arch, second_ssd, "SystemComposition")

    def binding_summary(path: Path):
        with SSD(path, mode="r") as ssd:
            [binding] = ssd.xml.system.parameter_bindings
            entries = (
                []
                if binding.parameter_mapping is None
                else [
                    (mapping.source, mapping.target)
                    for mapping in binding.parameter_mapping.mapping.mappings
                ]
            )
            component = ssd.xml.system.elements[0]
            connectors = [
                (connector.name, connector.kind, connector.type_name)
                for connector in component.connectors
            ]
            return binding.source, binding.prefix, entries, connectors

    assert binding_summary(first_ssd) == binding_summary(second_ssd)
