from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from pyssp_standard import SSD, SSM, SSV

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
        top = ssd.new_system("ScalarExample")
        ssd.rename("ScalarExample")

        src = top.add_component("src", source="resources/Source.fmu")
        src.add_connector(name="signal", kind="output", type_name="Real")

        dst = top.add_component("dst", source="resources/Sink.fmu")
        dst.add_connector(name="signal", kind="input", type_name="Real")

        top.add_connection(
            start_element="src",
            start_connector="signal",
            end_element="dst",
            end_connector="signal",
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
        top = ssd.new_system("EnumMix")
        ssd.rename("EnumMix")

        src = top.add_component("src", source="resources/Source.fmu")
        src.add_connector(
            name="signal.Aircraft_State", kind="output", type_name="Integer"
        )
        src.add_connector(name="signal.TLiquid", kind="output", type_name="Real")

        dst = top.add_component("dst", source="resources/Sink.fmu")
        dst.add_connector(
            name="signal.Aircraft_State",
            kind="input",
            type_name="Enumeration",
            type_attributes={"name": "FlightPhase"},
        )
        dst.add_connector(name="signal.TLiquid", kind="input", type_name="Real")

        top.add_connection(
            start_element="src",
            start_connector="signal.Aircraft_State",
            end_element="dst",
            end_connector="signal.Aircraft_State",
        )
        top.add_connection(
            start_element="src",
            start_connector="signal.TLiquid",
            end_element="dst",
            end_connector="signal.TLiquid",
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
        top = ssd.new_system("ScalarGroup")
        ssd.rename("ScalarGroup")

        src = top.add_component("src", source="resources/Source.fmu")
        src.add_connector(name="signal.value", kind="output", type_name="Real")

        dst = top.add_component("dst", source="resources/Sink.fmu")
        dst.add_connector(name="signal.in.y", kind="input", type_name="Real")

        top.add_connection(
            start_element="src",
            start_connector="signal.value",
            end_element="dst",
            end_connector="signal.in.y",
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
        top = ssd.new_system("ParamDemo")
        ssd.rename("ParamDemo")
        top.add_parameter_binding("parameters.ssv", prefix="gain")

        gain = top.add_component("gain", source="resources/Gain.fmu")
        gain.add_connector(name="k", kind="parameter", type_name="Real")

    output = tmp_path / "architecture.sysml"
    generate_sysml_from_ssd(ssd_path, output)
    text = output.read_text()

    assert "port def GainParameters :> ParameterInterface {" in text
    assert "attribute k : Real;" in text
    assert "in port parameters : GainParameters;" in text
    assert "attribute def parameters :> ParameterSet {" in text
    assert "attribute k : Real = 3.0;" in text
    assert "attribute parameters_set : parameters;" in text
    assert "bind gain.parameters = parameters_set;" in text


def test_generate_sysml_from_ssd_synthesizes_explicit_parameter_mapping(
    tmp_path: Path,
) -> None:
    """Inline SSM entries become per-member binds with list expansion."""
    parameter_set = SSV.create_parameter_set("Nom")
    parameter_set.add_parameter("n", "Integer", value=5)
    parameter_set.add_parameter("x[0]", "Real", value=1.0)
    parameter_set.add_parameter("x[1]", "Real", value=2.0)
    mapping = SSM.create_mapping(
        [("n", "comp.count"), ("x[0]", "comp.xs[0]"), ("x[1]", "comp.xs[1]")]
    )

    ssd_path = tmp_path / "SystemStructure.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        top = ssd.new_system("ParamDemo")
        ssd.rename("ParamDemo")
        top.add_parameter_binding(None, parameter_set=parameter_set, mapping=mapping)

        comp = top.add_component("comp", source="resources/Comp.fmu")
        comp.add_connector(name="count", kind="parameter", type_name="Integer")
        comp.add_connector(name="xs[0]", kind="parameter", type_name="Real")
        comp.add_connector(name="xs[1]", kind="parameter", type_name="Real")

    output = tmp_path / "architecture.sysml"
    generate_sysml_from_ssd(ssd_path, output)
    text = output.read_text()

    assert "port def CompParameters :> ParameterInterface {" in text
    assert "attribute count : Integer;" in text
    assert "attribute xs : Real[2];" in text
    assert "attribute def Nom :> ParameterSet {" in text
    assert "attribute n : Integer = 5;" in text
    assert "attribute x : Real[2] = (1.0, 2.0);" in text
    assert "attribute Nom : Nom;" in text
    assert "bind comp.parameters.count = Nom.n;" in text
    assert "bind comp.parameters.xs = Nom.x;" in text


def test_generate_sysml_from_ssd_uses_component_inline_parameter_set(
    tmp_path: Path,
) -> None:
    """A component-level inline ParameterValues applies to its owning component."""
    parameter_set = SSV.create_parameter_set("parameters")
    parameter_set.add_parameter("k", "Real", value=4.0)

    ssd_path = tmp_path / "SystemStructure.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        top = ssd.new_system("ParamDemo")
        ssd.rename("ParamDemo")

        gain = top.add_component("gain", source="resources/Gain.fmu")
        gain.add_connector(name="k", kind="parameter", type_name="Real")
        gain.add_parameter_binding(None, parameter_set=parameter_set)

    output = tmp_path / "architecture.sysml"
    generate_sysml_from_ssd(ssd_path, output)
    text = output.read_text()

    assert "attribute def parameters :> ParameterSet {" in text
    assert "attribute k : Real = 4.0;" in text
    assert "bind gain.parameters = parameters_set;" in text


def test_generate_sysml_from_ssd_keeps_interface_without_binding(
    tmp_path: Path,
) -> None:
    """Parameter connectors still define an interface when no set is applied."""
    ssd_path = tmp_path / "SystemStructure.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        top = ssd.new_system("ParamDemo")
        ssd.rename("ParamDemo")

        gain = top.add_component("gain", source="resources/Gain.fmu")
        gain.add_connector(name="k", kind="parameter", type_name="Real")

    output = tmp_path / "architecture.sysml"
    generate_sysml_from_ssd(ssd_path, output)
    text = output.read_text()

    assert "port def GainParameters :> ParameterInterface {" in text
    assert "in port parameters : GainParameters;" in text
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
        top = ssd.new_system("ParamDemo")
        ssd.rename("ParamDemo")
        top.add_parameter_binding("parameters.ssv", mapping_source="mapping.ssm")

        comp = top.add_component("comp", source="resources/Comp.fmu")
        comp.add_connector(name="count", kind="parameter", type_name="Integer")
        comp.add_connector(name="xs[0]", kind="parameter", type_name="Real")
        comp.add_connector(name="xs[1]", kind="parameter", type_name="Real")

    output = tmp_path / "architecture.sysml"
    generate_sysml_from_ssd(ssd_path, output)
    text = output.read_text()

    assert "bind comp.parameters.count = Nom.n;" in text
    assert "bind comp.parameters.xs = Nom.x;" in text


def test_generate_sysml_rejects_reserved_parameter_name(tmp_path: Path) -> None:
    """Reserved SysML keywords cannot become parameter feature names."""
    ssd_path = tmp_path / "SystemStructure.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        top = ssd.new_system("ParamDemo")
        ssd.rename("ParamDemo")

        comp = top.add_component("comp", source="resources/Comp.fmu")
        comp.add_connector(name="part", kind="parameter", type_name="Real")

    with pytest.raises(ValueError, match="cannot be represented"):
        generate_sysml_from_ssd(ssd_path, tmp_path / "architecture.sysml")


def test_generate_sysml_from_ssd_resolves_nested_system_binding(
    tmp_path: Path,
) -> None:
    """A binding inside a nested SSD system is resolved relative to that system."""
    (tmp_path / "parameters.ssv").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<ssv:ParameterSet xmlns:ssv="http://ssp-standard.org/SSP1/SystemStructureParameterValues" version="1.0" name="Nom">
  <ssv:Parameters>
    <ssv:Parameter name="inner.k"><ssv:Real value="3.0" /></ssv:Parameter>
  </ssv:Parameters>
</ssv:ParameterSet>
"""
    )
    ssd_path = tmp_path / "SystemStructure.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        top = ssd.new_system("Demo")
        ssd.rename("Demo")

        outer = top.add_subsystem("outer")

        inner = outer.add_component("inner", source="resources/Inner.fmu")
        inner.add_connector(name="k", kind="parameter", type_name="Real")
        outer.add_parameter_binding("parameters.ssv")

    output = tmp_path / "architecture.sysml"
    generate_sysml_from_ssd(ssd_path, output)
    text = output.read_text()

    assert "part inner : Inner;" in text
    assert "bind outer.inner.parameters = Nom;" in text


def test_generate_sysml_from_ssd_keeps_boundary_connections(tmp_path: Path) -> None:
    """A connection end without an element becomes a bare port reference."""
    ssd_path = tmp_path / "boundary.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        top = ssd.new_system("BoundaryExample")
        ssd.rename("BoundaryExample")
        top.add_connector(name="y", kind="output", type_name="Real")

        inner = top.add_subsystem("inner")
        inner.add_connector(name="u", kind="input", type_name="Real")
        inner.add_connector(name="v", kind="output", type_name="Real")
        src = inner.add_component("src", source="resources/Source.fmu")
        src.add_connector(name="sig", kind="output", type_name="Real")

        dst = inner.add_component("dst", source="resources/Sink.fmu")
        dst.add_connector(name="sigIn", kind="input", type_name="Real")
        dst.add_connector(name="sig", kind="output", type_name="Real")

        inner.add_connection(start_connector="u", end_element="src", end_connector="sig")
        inner.add_connection(
            start_element="src",
            start_connector="sig",
            end_element="dst",
            end_connector="sigIn",
        )
        inner.add_connection(
            start_element="dst", start_connector="sig", end_connector="v"
        )
        top.add_connection(
            start_element="inner", start_connector="v", end_connector="y"
        )

    output = tmp_path / "boundary.sysml"
    generate_sysml_from_ssd(ssd_path, output)
    text = _architecture_text(output)

    assert "connect u to src.sig;" in text
    assert "connect dst.sig to v;" in text
    assert "connect inner.v to y;" in text


def test_generate_sysml_from_ssd_rejects_unknown_boundary_port(tmp_path: Path) -> None:
    """A boundary connection must reference a declared system connector."""
    ssd_path = tmp_path / "boundary.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        top = ssd.new_system("BoundaryExample")
        ssd.rename("BoundaryExample")

        src = top.add_component("src", source="resources/Source.fmu")
        src.add_connector(name="sig", kind="output", type_name="Real")
        top.add_connection(
            start_element="src", start_connector="sig", end_connector="y"
        )

    with pytest.raises(ValueError, match="boundary port"):
        generate_sysml_from_ssd(ssd_path, tmp_path / "boundary.sysml")


def test_generate_sysml_from_ssd_writes_boundary_connections(tmp_path: Path) -> None:
    """An SSD connection without an element becomes a bare-name connect."""
    ssd_path = tmp_path / "boundary.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        top = ssd.new_system("Boundary")
        ssd.rename("Boundary")
        top.add_connector(name="y.x", kind="output", type_name="Real")

        inner = top.add_subsystem("inner")
        inner.add_connector(name="u.x", kind="input", type_name="Real")
        inner.add_connector(name="v.x", kind="output", type_name="Real")
        src = inner.add_component("src", source="resources/Source.fmu")
        src.add_connector(name="sig.x", kind="output", type_name="Real")
        dst = inner.add_component("dst", source="resources/Sink.fmu")
        dst.add_connector(name="sigIn.x", kind="input", type_name="Real")
        dst.add_connector(name="sig.x", kind="output", type_name="Real")
        inner.add_connection(
            start_connector="u.x", end_element="src", end_connector="sig.x"
        )
        inner.add_connection(
            start_element="src",
            start_connector="sig.x",
            end_element="dst",
            end_connector="sigIn.x",
        )
        inner.add_connection(
            start_element="dst", start_connector="sig.x", end_connector="v.x"
        )
        top.add_connection(
            start_element="inner", start_connector="v.x", end_connector="y.x"
        )

    output = tmp_path / "boundary.sysml"
    generate_sysml_from_ssd(ssd_path, output)
    text = _architecture_text(output)

    assert "connect u to src.sig;" in text
    assert "connect dst.sig to v;" in text
    assert "connect inner.v to y;" in text
