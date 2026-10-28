"""Regression tests for SSD -> SysML -> SSD fidelity."""

from __future__ import annotations

from pathlib import Path

from pyssp_standard import Component, SSD, System

from pyssp_sysml2.artifacts.fmi import generate_model_descriptions
from pyssp_sysml2.artifacts.ssd import generate_ssd
from pyssp_sysml2.artifacts.ssm import generate_parameter_mappings
from pyssp_sysml2.artifacts.ssv import generate_parameter_sets
from pyssp_sysml2.sysml.generate import generate_sysml_from_ssd
from pyssp_sysml2.model import load
from tests.fixture_files import fixture_text
from tests.testhelpers import write_model


def _write_reference_ssp(root: Path) -> Path:
    root.mkdir(parents=True)
    parameter_path = root / "parameters.ssv"
    parameter_path.write_text(
        fixture_text("roundtrip/parameters.ssv")
    )

    ssd_path = root / "SystemStructure.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        top = ssd.new_system("RoundTrip")
        ssd.rename("RoundTrip")
        top.add_parameter_binding("parameters.ssv")

        gain = top.add_component(
            "gain",
            source="resources/Gain.fmu",
            implementation="CoSimulation",
        )
        gain.add_connector(name="k", kind="parameter", type_name="Real")
        gain.add_connector(name="u", kind="input", type_name="Real")
        gain.add_connector(name="y", kind="output", type_name="Real")

        ssd.set_default_experiment(start_time=0.0, stop_time=2.0)
    return ssd_path


def test_ssd_sysml_ssd_preserves_metadata(tmp_path: Path) -> None:
    ssd_path = _write_reference_ssp(tmp_path / "source")
    architecture_dir = tmp_path / "architecture"
    architecture_dir.mkdir()
    generated = architecture_dir / "architecture.sysml"
    generate_sysml_from_ssd(ssd_path, generated)

    generated_text = generated.read_text()
    assert "port def GainParameters :> ParameterInterface" in generated_text
    assert "attribute def parameters :> ParameterSet" in generated_text
    assert "attribute parameters_set : parameters;" in generated_text
    assert "bind gain.parameters = parameters_set;" in generated_text
    assert "attribute def FmuMetadata {" in generated_text
    assert "attribute def GainFmuMetadata :> FmuMetadata {" in generated_text
    assert 'attribute implementation : String = "CoSimulation";' in generated_text
    assert "attribute fmu_meta : GainFmuMetadata;" in generated_text

    regenerated = tmp_path / "regenerated.ssd"
    generate_ssd(architecture_dir, regenerated, "RoundTrip")

    with SSD(regenerated, mode="r") as ssd:
        assert ssd.default_experiment.start_time == 0.0
        assert ssd.default_experiment.stop_time == 2.0
        [binding] = ssd.system.parameter_bindings
        assert binding.source == "parameter_sets/parameters.ssv"
        assert binding.prefix == "gain"
        assert binding.parameter_mapping is None

        component = ssd.system.elements[0]
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
        fixture_text("roundtrip/explicit-parameter-mapping.sysml")
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
            [binding] = ssd.system.parameter_bindings
            entries = (
                []
                if binding.parameter_mapping is None
                else [
                    (mapping.source, mapping.target)
                    for mapping in binding.parameter_mapping.mapping.mappings
                ]
            )
            component = ssd.system.elements[0]
            connectors = [
                (connector.name, connector.kind, connector.type_name)
                for connector in component.connectors
            ]
            return binding.source, binding.prefix, entries, connectors

    assert binding_summary(first_ssd) == binding_summary(second_ssd)


def test_nested_parameter_path_roundtrip(tmp_path: Path) -> None:
    """A set applied to a nested part path survives SSD round-trips."""
    architecture_dir = tmp_path / "source_arch"
    write_model(
        architecture_dir / "model.sysml",
        fixture_text("roundtrip/nested-parameter-model.sysml")
    )

    first_ssd = tmp_path / "source" / "SystemStructure.ssd"
    generate_ssd(architecture_dir, first_ssd, "SystemComposition")
    generate_parameter_sets(
        architecture_dir,
        first_ssd.parent / "parameter_sets",
        "SystemComposition",
    )

    with SSD(first_ssd, mode="r") as ssd:
        top = ssd.system
        assert [element.name for element in top.elements] == ["outer"]
        outer = top.elements[0]
        assert isinstance(outer, System)
        assert [element.name for element in outer.elements] == ["inner"]
        inner = outer.elements[0]
        assert isinstance(inner, Component)
        assert [
            (connector.name, connector.kind)
            for connector in inner.connectors
        ] == [("k", "parameter")]
        [binding] = top.parameter_bindings
        assert [
            (mapping.source, mapping.target)
            for mapping in binding.parameter_mapping.mapping.mappings
        ] == [("k", "outer.inner.k")]

    roundtrip_arch = tmp_path / "roundtrip_arch"
    roundtrip_arch.mkdir()
    generated = roundtrip_arch / "architecture.sysml"
    generate_sysml_from_ssd(first_ssd, generated)
    text = generated.read_text()
    assert "port def innerParameters :> ParameterInterface" in text
    assert "part def outer" in text
    assert "part inner : inner;" in text
    assert "bind outer.inner.parameters.k = Nom.k;" in text

    second_ssd = tmp_path / "regenerated.ssd"
    generate_ssd(roundtrip_arch, second_ssd, "SystemComposition")
    with SSD(second_ssd, mode="r") as ssd:
        top = ssd.system
        assert [element.name for element in top.elements] == ["outer"]
        [binding] = top.parameter_bindings
        assert [
            (mapping.source, mapping.target)
            for mapping in binding.parameter_mapping.mapping.mappings
        ] == [("k", "outer.inner.k")]

    model_descriptions = generate_model_descriptions(
        architecture_dir,
        tmp_path / "model_descriptions",
        "SystemComposition",
    )
    assert [path.parent.name for path in model_descriptions] == ["Inner"]


def test_nested_multiple_disjoint_sets_roundtrip(tmp_path: Path) -> None:
    """Multiple sets at a nested component path keep disjoint mappings."""
    architecture_dir = tmp_path / "source_arch"
    write_model(
        architecture_dir / "model.sysml",
        fixture_text("roundtrip/multiple-disjoint-sets.sysml")
    )

    first_ssd = tmp_path / "source" / "SystemStructure.ssd"
    generate_ssd(architecture_dir, first_ssd, "SystemComposition")
    generate_parameter_sets(
        architecture_dir,
        first_ssd.parent / "parameter_sets",
        "SystemComposition",
    )
    mappings = generate_parameter_mappings(
        architecture_dir, tmp_path / "mappings", "SystemComposition"
    )
    assert [path.name for path in mappings] == [
        "Counts_outer_inner.ssm",
        "Gains_outer_inner.ssm",
    ]

    def binding_summary(path: Path):
        with SSD(path, mode="r") as ssd:
            return sorted(
                (
                    binding.source,
                    [
                        (mapping.source, mapping.target)
                        for mapping in binding.parameter_mapping.mapping.mappings
                    ],
                )
                for binding in ssd.system.parameter_bindings
            )

    assert binding_summary(first_ssd) == [
        ("parameter_sets/Counts.ssv", [("n", "outer.inner.count")]),
        ("parameter_sets/Gains.ssv", [("k", "outer.inner.gain")]),
    ]

    roundtrip_arch = tmp_path / "roundtrip_arch"
    roundtrip_arch.mkdir()
    generated = roundtrip_arch / "architecture.sysml"
    generate_sysml_from_ssd(first_ssd, generated)
    text = generated.read_text()
    assert "bind outer.inner.parameters.count = Counts.n;" in text
    assert "bind outer.inner.parameters.gain = Gains.k;" in text

    second_ssd = tmp_path / "regenerated.ssd"
    generate_ssd(roundtrip_arch, second_ssd, "SystemComposition")
    assert binding_summary(second_ssd) == binding_summary(first_ssd)


def test_nested_system_parameter_port_roundtrip(tmp_path: Path) -> None:
    """A nested system can own a parameter interface alongside subparts."""
    architecture_dir = tmp_path / "source_arch"
    write_model(
        architecture_dir / "model.sysml",
        fixture_text("roundtrip/nested-system-parameter-port.sysml")
    )

    first_ssd = tmp_path / "source" / "SystemStructure.ssd"
    generate_ssd(architecture_dir, first_ssd, "SystemComposition")
    generate_parameter_sets(
        architecture_dir,
        first_ssd.parent / "parameter_sets",
        "SystemComposition",
    )

    with SSD(first_ssd, mode="r") as ssd:
        outer = ssd.system.elements[0]
        assert isinstance(outer, System)
        assert [
            (connector.name, connector.kind)
            for connector in outer.connectors
        ] == [("gain", "parameter")]
        assert [
            (binding.source, mapping.target)
            for binding in ssd.system.parameter_bindings
            for mapping in binding.parameter_mapping.mapping.mappings
        ] == [
            ("parameter_sets/OuterSet.ssv", "outer.gain"),
            ("parameter_sets/InnerSet.ssv", "outer.inner.k"),
        ]

    roundtrip_arch = tmp_path / "roundtrip_arch"
    roundtrip_arch.mkdir()
    generated = roundtrip_arch / "architecture.sysml"
    generate_sysml_from_ssd(first_ssd, generated)
    text = generated.read_text()
    assert "part def outer" in text
    assert "in port parameters : outerParameters;" in text
    assert "bind outer.parameters.gain = OuterSet.g;" in text
    assert "bind outer.inner.parameters.k = InnerSet.k;" in text

    second_ssd = tmp_path / "regenerated.ssd"
    generate_ssd(roundtrip_arch, second_ssd, "SystemComposition")
    with SSD(second_ssd, mode="r") as ssd:
        assert [
            (binding.source, mapping.target)
            for binding in ssd.system.parameter_bindings
            for mapping in binding.parameter_mapping.mapping.mappings
        ] == [
            ("parameter_sets/OuterSet.ssv", "outer.gain"),
            ("parameter_sets/InnerSet.ssv", "outer.inner.k"),
        ]


def _wiring(ssd_path: Path) -> list[tuple[str, str, str | None, str | None]]:
    """All connections of the top system and its nested systems."""
    with SSD(ssd_path, mode="r") as ssd:
        top = ssd.system

    result = []
    for element in top.elements:
        if isinstance(element, System):
            result.extend(
                (c.start_element, c.start_connector, c.end_element, c.end_connector)
                for c in element.connections
            )
    result.extend(
        (c.start_element, c.start_connector, c.end_element, c.end_connector)
        for c in top.connections
    )
    return sorted(
        result,
        key=lambda item: tuple("" if value is None else value for value in item),
    )


def test_boundary_connections_roundtrip(tmp_path: Path) -> None:
    """Boundary connections survive SSD -> SysML -> SSD unchanged."""
    architecture_dir = tmp_path / "source_arch"
    write_model(
        architecture_dir / "model.sysml",
        fixture_text("roundtrip/boundary-connections.sysml")
    )

    first_ssd = tmp_path / "source" / "SystemStructure.ssd"
    generate_ssd(architecture_dir, first_ssd, "SystemComposition")

    roundtrip_arch = tmp_path / "roundtrip_arch"
    roundtrip_arch.mkdir()
    generated = roundtrip_arch / "architecture.sysml"
    generate_sysml_from_ssd(first_ssd, generated)

    text = generated.read_text()
    assert "connect u to src.sig;" in text
    assert "connect dst.sig to v;" in text
    assert "connect inner.v to y;" in text

    second_ssd = tmp_path / "regenerated.ssd"
    generate_ssd(roundtrip_arch, second_ssd, "SystemComposition")

    assert _wiring(second_ssd) == _wiring(first_ssd)


def test_string_escapes_roundtrip(tmp_path: Path) -> None:
    """Newlines and escapes survive SysML -> SysML without raw literals."""
    architecture_dir = tmp_path / "arch"
    write_model(
        architecture_dir / "model.sysml",
        fixture_text("roundtrip/string-escapes.sysml")
    )

    architecture = load(architecture_dir)
    exported = architecture.export_declared()["model.sysml"]
    assert r'"one\ntwo"' in exported
    assert r'"C:\\temp\\new"' in exported

    generated = tmp_path / "generated.sysml"
    generated.write_text(exported, encoding="utf-8")
    reloaded = load(generated)

    attributes = reloaded.part_definitions["Text"].attributes
    assert attributes["lines"].value == "one\ntwo"
    assert attributes["path"].value == r"C:\temp\new"
