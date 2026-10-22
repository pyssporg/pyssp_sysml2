from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from pyssp_standard.ssd import (
    Component,
    Connection,
    Connector,
    ParameterBinding,
    SSD,
    System,
)
from pyssp_standard.ssm import SSM
from pyssp_standard.standard.ssp1.model import (
    Ssd1ParameterMappingReference,
    Ssp1ParameterMapping,
    Ssp1ParameterSet,
)

from pyssp_sysml2.sysml import generate_sysml_from_ssd
from pyssp_sysml2.sysml_model import load
from tests.test_utils import write_bootstrap_ssd


def _architecture_text(path: Path) -> str:
    files = load(path).export_declared()
    return "\n".join(files[name] for name in sorted(files))


def test_generate_sysml_from_ssd_uses_ssd_system_name_by_default(tmp_path: Path) -> None:
    """Generating SysML from SSD writes a minimal single-file architecture."""
    ssd_path = write_bootstrap_ssd(tmp_path / "SystemStructure.ssd")
    output = tmp_path / "generated" / "architecture.sysml"

    written = generate_sysml_from_ssd(ssd_path, output)

    assert written == output
    assert _architecture_text(output) == dedent(
        """
        package RecoveredFromSSD {
          port def Port_1 {
            attribute x : Real;
            attribute y : Real;
          }

          part def Sink {
            in port inSig : Port_1;
          }

          part def Source {
            out port outSig : Port_1;
          }

          part def SystemComposition {
            part dst : Sink;
            part src : Source;
            connect src.outSig to dst.inSig;
          }
        }
        """
    ).strip() + "\n"


def test_generate_sysml_from_ssd_allows_overriding_composition_name(tmp_path: Path) -> None:
    """Generating SysML from SSD can override the top-level composition name."""
    ssd_path = write_bootstrap_ssd(tmp_path / "SystemStructure.ssd")
    output = tmp_path / "architecture.sysml"

    generate_sysml_from_ssd(ssd_path, output, composition="RecoveredComposition")

    assert "part def RecoveredComposition" in _architecture_text(output)


def test_generate_sysml_from_ssd_supports_scalar_connectors(tmp_path: Path) -> None:
    """Generating SysML from SSD tolerates scalar connector names without dotted attributes."""
    ssd_path = tmp_path / "scalar.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        ssd.xml.name = "ScalarExample"
        ssd.xml.version = "1.0"
        ssd.xml.system = System(name="ScalarExample")

        src = Component()
        src.name = "src"
        src.source = "resources/Source.fmu"
        src.connectors.append(Connector(name="signal", kind="output", type_name="Real"))
        ssd.xml.system.elements.append(src)

        dst = Component()
        dst.name = "dst"
        dst.source = "resources/Sink.fmu"
        dst.connectors.append(Connector(name="signal", kind="input", type_name="Real"))
        ssd.xml.system.elements.append(dst)

        ssd.xml.system.connections.append(
            Connection(
                start_element="src",
                start_connector="signal",
                end_element="dst",
                end_connector="signal",
            )
        )

    output = tmp_path / "scalar.sysml"
    generate_sysml_from_ssd(ssd_path, output)

    assert _architecture_text(output) == dedent(
        """
        package RecoveredFromSSD {
          port def Port_1 {
            attribute pyssp_flat_connector : Boolean = true;
            attribute value : Real;
          }

          part def ScalarExample {
            part dst : Sink;
            part src : Source;
            connect src.signal to dst.signal;
          }

          part def Sink {
            in port signal : Port_1;
          }

          part def Source {
            out port signal : Port_1;
          }
        }
        """
    ).strip() + "\n"


def test_generate_sysml_from_ssd_reuses_connected_port_type_for_enum_and_integer_mix(
    tmp_path: Path,
) -> None:
    ssd_path = tmp_path / "enum_mix.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        ssd.xml.name = "EnumMix"
        ssd.xml.version = "1.0"
        ssd.xml.system = System(name="EnumMix")

        src = Component()
        src.name = "src"
        src.source = "resources/Source.fmu"
        src.connectors.extend(
            [
                Connector(name="signal.Aircraft_State", kind="output", type_name="Integer"),
                Connector(name="signal.TLiquid", kind="output", type_name="Real"),
            ]
        )
        ssd.xml.system.elements.append(src)

        dst = Component()
        dst.name = "dst"
        dst.source = "resources/Sink.fmu"
        dst.connectors.extend(
            [
                Connector(
                    name="signal.Aircraft_State",
                    kind="input",
                    type_name="Enumeration",
                    type_attributes={"name": "FlightPhase"},
                ),
                Connector(name="signal.TLiquid", kind="input", type_name="Real"),
            ]
        )
        ssd.xml.system.elements.append(dst)

        ssd.xml.system.connections.extend(
            [
                Connection(
                    start_element="src",
                    start_connector="signal.Aircraft_State",
                    end_element="dst",
                    end_connector="signal.Aircraft_State",
                ),
                Connection(
                    start_element="src",
                    start_connector="signal.TLiquid",
                    end_element="dst",
                    end_connector="signal.TLiquid",
                ),
            ]
        )

    output = tmp_path / "enum_mix.sysml"
    generate_sysml_from_ssd(ssd_path, output)
    text = _architecture_text(output)

    assert text.count("Port_1") == 3
    assert "Port_2" not in text
    assert "attribute Aircraft_State : Integer;" in text
    assert "in port signal : Port_1;" in text
    assert "out port signal : Port_1;" in text


def test_generate_sysml_from_ssd_normalizes_scalar_group_attribute_names(tmp_path: Path) -> None:
    ssd_path = tmp_path / "scalar_group.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        ssd.xml.name = "ScalarGroup"
        ssd.xml.version = "1.0"
        ssd.xml.system = System(name="ScalarGroup")

        src = Component()
        src.name = "src"
        src.source = "resources/Source.fmu"
        src.connectors.append(Connector(name="signal.value", kind="output", type_name="Real"))
        ssd.xml.system.elements.append(src)

        dst = Component()
        dst.name = "dst"
        dst.source = "resources/Sink.fmu"
        dst.connectors.append(Connector(name="signal.in.y", kind="input", type_name="Real"))
        ssd.xml.system.elements.append(dst)

        ssd.xml.system.connections.append(
            Connection(
                start_element="src",
                start_connector="signal.value",
                end_element="dst",
                end_connector="signal.in.y",
            )
        )

    output = tmp_path / "scalar_group.sysml"
    generate_sysml_from_ssd(ssd_path, output)
    text = _architecture_text(output)

    assert text.count("Port_1") == 3
    assert "Port_2" not in text
    assert "attribute value : Real;" in text


def test_generate_sysml_from_ssd_synthesizes_identity_parameter_binding(
    tmp_path: Path,
) -> None:
    """A prefixed SSD ParameterBinding becomes an interface, set, and identity bind."""
    (tmp_path / "parameters.ssv").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<ssv:ParameterSet xmlns:ssv="http://ssp-standard.org/SSP1/SystemStructureParameterValues" version="1.0" name="parameters">
  <ssv:Parameters>
    <ssv:Parameter name="k"><ssv:Real value="3.0" /></ssv:Parameter>
  </ssv:Parameters>
</ssv:ParameterSet>
"""
    )
    ssd_path = tmp_path / "SystemStructure.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        ssd.xml.name = "ParamDemo"
        ssd.xml.version = "1.0"
        ssd.xml.system = System(name="ParamDemo")
        ssd.xml.system.parameter_bindings = [
            ParameterBinding(source="parameters.ssv", prefix="gain")
        ]

        gain = Component()
        gain.name = "gain"
        gain.source = "resources/Gain.fmu"
        gain.connectors.append(Connector(name="k", kind="parameter", type_name="Real"))
        ssd.xml.system.elements.append(gain)

    output = tmp_path / "architecture.sysml"
    generate_sysml_from_ssd(ssd_path, output)
    text = output.read_text()

    assert "attribute def GainParameters :> ParameterInterface {" in text
    assert "attribute k : Real;" in text
    assert "attribute parameters : GainParameters;" in text
    assert "attribute def parameters :> ParameterSet {" in text
    assert "attribute k : Real = 3.0;" in text
    assert "attribute parameters_set : parameters;" in text
    assert "bind parameters_set = gain.parameters;" in text


def test_generate_sysml_from_ssd_synthesizes_explicit_parameter_mapping(
    tmp_path: Path,
) -> None:
    """Inline SSM entries become per-member binds with list expansion."""
    parameter_set = Ssp1ParameterSet(name="Nom", version="1.0")
    parameter_set.add_parameter("n", "Integer", value=5)
    parameter_set.add_parameter("x[0]", "Real", value=1.0)
    parameter_set.add_parameter("x[1]", "Real", value=2.0)
    mapping = Ssp1ParameterMapping(version="1.0")
    mapping.add_mapping("n", "comp.count")
    mapping.add_mapping("x[0]", "comp.xs[0]")
    mapping.add_mapping("x[1]", "comp.xs[1]")

    ssd_path = tmp_path / "SystemStructure.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        ssd.xml.name = "ParamDemo"
        ssd.xml.version = "1.0"
        ssd.xml.system = System(name="ParamDemo")
        ssd.xml.system.parameter_bindings = [
            ParameterBinding(
                parameter_set=parameter_set,
                parameter_mapping=Ssd1ParameterMappingReference(mapping=mapping),
            )
        ]

        comp = Component()
        comp.name = "comp"
        comp.source = "resources/Comp.fmu"
        comp.connectors.extend(
            [
                Connector(name="count", kind="parameter", type_name="Integer"),
                Connector(name="xs[0]", kind="parameter", type_name="Real"),
                Connector(name="xs[1]", kind="parameter", type_name="Real"),
            ]
        )
        ssd.xml.system.elements.append(comp)

    output = tmp_path / "architecture.sysml"
    generate_sysml_from_ssd(ssd_path, output)
    text = output.read_text()

    assert "attribute def CompParameters :> ParameterInterface {" in text
    assert "attribute count : Integer;" in text
    assert "attribute xs : Real[2];" in text
    assert "attribute def Nom :> ParameterSet {" in text
    assert "attribute n : Integer = 5;" in text
    assert "attribute x : Real[2] = (1.0, 2.0);" in text
    assert "attribute Nom : Nom;" in text
    assert "bind Nom.n = comp.parameters.count;" in text
    assert "bind Nom.x = comp.parameters.xs;" in text


def test_generate_sysml_from_ssd_uses_component_inline_parameter_set(
    tmp_path: Path,
) -> None:
    """A component-level inline ParameterValues applies to its owning component."""
    parameter_set = Ssp1ParameterSet(name="parameters", version="1.0")
    parameter_set.add_parameter("k", "Real", value=4.0)

    ssd_path = tmp_path / "SystemStructure.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        ssd.xml.name = "ParamDemo"
        ssd.xml.version = "1.0"
        ssd.xml.system = System(name="ParamDemo")

        gain = Component()
        gain.name = "gain"
        gain.source = "resources/Gain.fmu"
        gain.connectors.append(Connector(name="k", kind="parameter", type_name="Real"))
        gain.parameter_bindings.append(ParameterBinding(parameter_set=parameter_set))
        ssd.xml.system.elements.append(gain)

    output = tmp_path / "architecture.sysml"
    generate_sysml_from_ssd(ssd_path, output)
    text = output.read_text()

    assert "attribute def parameters :> ParameterSet {" in text
    assert "attribute k : Real = 4.0;" in text
    assert "bind parameters_set = gain.parameters;" in text


def test_generate_sysml_from_ssd_keeps_interface_without_binding(
    tmp_path: Path,
) -> None:
    """Parameter connectors still define an interface when no set is applied."""
    ssd_path = tmp_path / "SystemStructure.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        ssd.xml.name = "ParamDemo"
        ssd.xml.version = "1.0"
        ssd.xml.system = System(name="ParamDemo")

        gain = Component()
        gain.name = "gain"
        gain.source = "resources/Gain.fmu"
        gain.connectors.append(Connector(name="k", kind="parameter", type_name="Real"))
        ssd.xml.system.elements.append(gain)

    output = tmp_path / "architecture.sysml"
    generate_sysml_from_ssd(ssd_path, output)
    text = output.read_text()

    assert "attribute def GainParameters :> ParameterInterface {" in text
    assert "attribute parameters : GainParameters;" in text
    assert "ParameterSet {" not in text
    assert "bind " not in text


def test_generate_sysml_from_ssd_reads_external_ssm(tmp_path: Path) -> None:
    """ParameterMapping/@source is resolved relative to the SSD."""
    (tmp_path / "parameters.ssv").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<ssv:ParameterSet xmlns:ssv="http://ssp-standard.org/SSP1/SystemStructureParameterValues" version="1.0" name="Nom">
  <ssv:Parameters>
    <ssv:Parameter name="n"><ssv:Integer value="5" /></ssv:Parameter>
    <ssv:Parameter name="x[0]"><ssv:Real value="1.0" /></ssv:Parameter>
    <ssv:Parameter name="x[1]"><ssv:Real value="2.0" /></ssv:Parameter>
  </ssv:Parameters>
</ssv:ParameterSet>
"""
    )
    with SSM(tmp_path / "mapping.ssm", mode="w") as ssm:
        ssm.xml.add_mapping("n", "comp.count")
        ssm.xml.add_mapping("x[0]", "comp.xs[0]")
        ssm.xml.add_mapping("x[1]", "comp.xs[1]")

    ssd_path = tmp_path / "SystemStructure.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        ssd.xml.name = "ParamDemo"
        ssd.xml.version = "1.0"
        ssd.xml.system = System(name="ParamDemo")
        ssd.xml.system.parameter_bindings = [
            ParameterBinding(
                source="parameters.ssv",
                parameter_mapping=Ssd1ParameterMappingReference(
                    source="mapping.ssm"
                ),
            )
        ]

        comp = Component()
        comp.name = "comp"
        comp.source = "resources/Comp.fmu"
        comp.connectors.extend(
            [
                Connector(name="count", kind="parameter", type_name="Integer"),
                Connector(name="xs[0]", kind="parameter", type_name="Real"),
                Connector(name="xs[1]", kind="parameter", type_name="Real"),
            ]
        )
        ssd.xml.system.elements.append(comp)

    output = tmp_path / "architecture.sysml"
    generate_sysml_from_ssd(ssd_path, output)
    text = output.read_text()

    assert "bind Nom.n = comp.parameters.count;" in text
    assert "bind Nom.x = comp.parameters.xs;" in text


def test_generate_sysml_rejects_reserved_parameter_name(tmp_path: Path) -> None:
    """Reserved SysML keywords cannot become parameter feature names."""
    ssd_path = tmp_path / "SystemStructure.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        ssd.xml.name = "ParamDemo"
        ssd.xml.version = "1.0"
        ssd.xml.system = System(name="ParamDemo")

        comp = Component()
        comp.name = "comp"
        comp.source = "resources/Comp.fmu"
        comp.connectors.append(
            Connector(name="part", kind="parameter", type_name="Real")
        )
        ssd.xml.system.elements.append(comp)

    with pytest.raises(ValueError, match="cannot be represented"):
        generate_sysml_from_ssd(ssd_path, tmp_path / "architecture.sysml")
