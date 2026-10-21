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
from pyssp_sysml2.sysml import generate_sysml_from_ssd


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
    generate_sysml_from_ssd(ssd_path, architecture_dir / "architecture.sysml")

    regenerated = tmp_path / "regenerated.ssd"
    generate_ssd(architecture_dir, regenerated, "RoundTrip")

    with SSD(regenerated, mode="r") as ssd:
        assert ssd.xml.default_experiment.start_time == 0.0
        assert ssd.xml.default_experiment.stop_time == 2.0
        assert ssd.xml.system.parameter_bindings[0].source == "parameters.ssv"

        component = ssd.xml.system.elements[0]
        assert component.name == "gain"
        assert component.implementation == "CoSimulation"
        connectors = {connector.name: connector.kind for connector in component.connectors}
        assert connectors == {"k": "parameter", "u": "input", "y": "output"}
