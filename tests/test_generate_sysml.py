from __future__ import annotations

from pathlib import Path

import pytest
from pyssp_standard import SSD, SSM, SSV

from pyssp_sysml2.sysml.generate import generate_sysml_from_ssd
from pyssp_sysml2.model import load
from tests.fixture_files import assert_matches_fixture, fixture_text
from tests.testhelpers import write_bootstrap_ssd


def _architecture_text(path: Path) -> str:
    files = load(path).export_declared()
    return "\n".join(files[name] for name in sorted(files))


def test_generate_sysml_from_ssd_uses_ssd_system_name_by_default(tmp_path: Path) -> None:
    """Generating SysML from SSD writes a minimal single-file architecture."""
    ssd_path = write_bootstrap_ssd(tmp_path / "SystemStructure.ssd")
    output = tmp_path / "generated" / "architecture.sysml"

    written = generate_sysml_from_ssd(ssd_path, output)

    assert written == output
    assert_matches_fixture(_architecture_text(output), "generate-sysml/ssd-system-name.sysml")


def test_generate_sysml_from_ssd_allows_overriding_composition_name(tmp_path: Path) -> None:
    """Generating SysML from SSD can override the top-level composition name."""
    ssd_path = write_bootstrap_ssd(tmp_path / "SystemStructure.ssd")
    output = tmp_path / "architecture.sysml"

    generate_sysml_from_ssd(ssd_path, output, composition="RecoveredComposition")

    assert_matches_fixture(_architecture_text(output), "generate-sysml/composition-override.sysml")


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

    assert_matches_fixture(_architecture_text(output), "generate-sysml/scalar-connectors.sysml")


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

    assert_matches_fixture(text, "generate-sysml/enum-integer-mix.sysml")


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

    assert_matches_fixture(text, "generate-sysml/scalar-group-names.sysml")


def test_generate_sysml_from_ssd_synthesizes_identity_parameter_binding(
    tmp_path: Path,
) -> None:
    """A prefixed SSD ParameterBinding becomes an interface, set, and identity bind."""
    (tmp_path / "parameters.ssv").write_text(
        fixture_text("generate-sysml/identity-binding.ssv")
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

    assert_matches_fixture(text, "generate-sysml/identity-binding.sysml")


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

    assert_matches_fixture(text, "generate-sysml/explicit-parameter-mapping.sysml")


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

    assert_matches_fixture(text, "generate-sysml/component-inline-parameter-set.sysml")


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

    assert_matches_fixture(text, "generate-sysml/interface-without-binding.sysml")


def test_generate_sysml_from_ssd_reads_external_ssm(tmp_path: Path) -> None:
    """ParameterMapping/@source is resolved relative to the SSD."""
    (tmp_path / "parameters.ssv").write_text(
        fixture_text("generate-sysml/external-mapping.ssv")
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

    assert_matches_fixture(text, "generate-sysml/explicit-parameter-mapping.sysml")


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
        fixture_text("generate-sysml/nested-system-binding.ssv")
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

    assert_matches_fixture(text, "generate-sysml/nested-system-binding.sysml")


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

    assert_matches_fixture(text, "generate-sysml/boundary-connections.sysml")


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

    assert_matches_fixture(text, "generate-sysml/boundary-connections-dotted.sysml")
