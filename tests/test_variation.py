from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from pyssp_standard import SSD, SSP, SSV

from pyssp_sysml2.cli import _parse_selections, main
from pyssp_sysml2.artifacts.ssd import build_ssd, generate_ssd
from pyssp_sysml2.artifacts.ssp import generate_ssp
from pyssp_sysml2.artifacts.analysis import generate_analysis
from pyssp_sysml2.sysml.sync import sync_sysml_from_ssd
from pyssp_sysml2.sysml.generate import generate_sysml_from_ssd
from pyssp_sysml2.model import load
from pyssp_sysml2.parameters.variation import has_variation, resolve
from tests.fixture_files import fixture_text
from tests.testhelpers import write_bootstrap_ssd, write_model

# Whole documents from the variation-point examples, one file per behaviour.
USAGE_LEVEL_VARIATION = fixture_text("variation/usage-level.sysml")
CONNECTION_VARIATION = fixture_text("variation/connection.sysml")
PARAMETER_BINDING_VARIATION = fixture_text("variation/parameter-binding.sysml")
NESTED_BODY_VARIATION = fixture_text("variation/nested-body.sysml")


DEFINITION_VARIATION = fixture_text("variation/definition.sysml")

DEFINITION_VARIATION_FMU = fixture_text("variation/definition-fmu.sysml")

USAGE_VARIATION = fixture_text("variation/usage.sysml")

BODY_VARIATION = fixture_text("variation/body.sysml")

NESTED_VARIATION = fixture_text("variation/nested.sysml")

AMBIGUOUS_NAMES = fixture_text("variation/ambiguous-names.sysml")

NO_VARIATION = fixture_text("variation/no-variation.sysml")


def _load_architecture(tmp_path: Path, content: str):
    path = tmp_path / "architecture.sysml"
    write_model(path, content)
    return path, load(path)


def test_definition_variation_captures_variants(tmp_path: Path) -> None:
    """A variation definition keeps its flag and its variant members, not parts."""
    _, architecture = _load_architecture(tmp_path, DEFINITION_VARIATION)

    source_choice = architecture.part_definitions["SourceChoice"]
    assert source_choice.is_variation is True
    assert [
        (variant.name, variant.kind, variant.type_name)
        for variant in source_choice.variants
    ] == [
        ("stepImplementation", "part", "Step"),
        ("sineImplementation", "part", "Sine"),
    ]
    assert source_choice.parts == {}


def test_usage_level_variation_captures_variants(tmp_path: Path) -> None:
    """A ``variation part`` usage keeps its flag and its own variants."""
    _, architecture = _load_architecture(tmp_path, USAGE_VARIATION)

    system = architecture.part_definitions["System"]
    assert system.is_variation is False
    source = system.parts["source"]
    assert source.is_variation is True
    assert [(variant.name, variant.type_name) for variant in source.variants] == [
        ("stepSource", "Step"),
        ("sineSource", "Sine"),
    ]
    assert system.variants == []


def test_model_without_variation_stays_clean(tmp_path: Path) -> None:
    """An architecture with no variation construct reports no variation."""
    _, architecture = _load_architecture(tmp_path, NO_VARIATION)

    for definition in architecture.part_definitions.values():
        assert definition.is_variation is False
        assert definition.variants == []
        assert not any(usage.is_variation for usage in definition.parts.values())


def test_generate_ssd_rejects_unresolved_variation(tmp_path: Path) -> None:
    """Generation fails on the variation point, not on the missing ports."""
    path, _ = _load_architecture(tmp_path, DEFINITION_VARIATION)

    with pytest.raises(
        ValueError,
        match="'SourceChoice' in composition 'System' is not selected.*"
        "--select",
    ):
        generate_ssd(path, tmp_path / "out" / "SystemStructure.ssd", "System")


def test_generate_ssd_still_succeeds_without_variation(tmp_path: Path) -> None:
    """The new check stays inert for a composition without variation."""
    path, _ = _load_architecture(tmp_path, NO_VARIATION)

    output = generate_ssd(path, tmp_path / "out" / "SystemStructure.ssd", "System")
    assert output.exists()


def test_variant_member_with_a_body_loads(tmp_path: Path) -> None:
    """A variant with a body keeps its nested parts and connections."""
    _, architecture = _load_architecture(tmp_path, BODY_VARIATION)

    path_choice = architecture.part_definitions["PathChoice"]
    assert path_choice.is_variation is True
    assert [(variant.name, variant.type_name) for variant in path_choice.variants] == [
        ("directPath", None)
    ]
    body = path_choice.variants[0].body
    assert body is not None
    assert [(name, usage.type_name) for name, usage in body.parts.items()] == [
        ("gain", "Gain")
    ]
    assert [
        (
            conn.source_part,
            conn.source_port,
            conn.destination_part,
            conn.destination_port,
        )
        for conn in body.connections.values()
    ] == [(None, "u", "gain", "u"), ("gain", "y", None, "y")]
    assert path_choice.parts == {}


def _component_sources(output: Path) -> dict[str, str]:
    with SSD(output, mode="r") as ssd:
        assert ssd.system is not None
        return {element.name: element.source for element in ssd.system.elements}


def test_resolve_substitutes_the_selected_variant(tmp_path: Path) -> None:
    """Resolution rewrites the usage type on a copy and keeps the usage name."""
    _, architecture = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)

    resolved = resolve(architecture, "System", {"source": "stepImplementation"})

    assert resolved.part_definitions["System"].parts["source"].type_name == "Step"
    assert architecture.part_definitions["System"].parts["source"].type_name == (
        "SourceChoice"
    )
    assert list(resolved.part_definitions["System"].parts) == ["source", "gain"]


def test_generate_ssd_selects_step_fmu(tmp_path: Path) -> None:
    """The selected Step variant supplies the component source, name unchanged."""
    path, _ = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)

    output = generate_ssd(
        path,
        tmp_path / "out" / "SystemStructure.ssd",
        "System",
        selections={"source": "stepImplementation"},
    )

    sources = _component_sources(output)
    assert sources["source"] == "resources/Step.fmu"


def test_generate_ssd_selects_sine_fmu(tmp_path: Path) -> None:
    """The other variant changes the source but not the SSD component name."""
    path, _ = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)

    output = generate_ssd(
        path,
        tmp_path / "out" / "SystemStructure.ssd",
        "System",
        selections={"source": "sineImplementation"},
    )

    sources = _component_sources(output)
    assert sources["source"] == "resources/Sine.fmu"


def test_generate_ssp_uses_the_selected_variant(tmp_path: Path) -> None:
    """SSP packaging resolves the selection before building its SSD."""
    path, _ = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)

    with pytest.warns(UserWarning, match="FMU source is missing"):
        output = generate_ssp(
            path,
            tmp_path / "out" / "System.ssp",
            "System",
            allow_missing_fmus=True,
            selections={"source": "sineImplementation"},
        )

    with SSP(output, mode="r") as ssp:
        with ssp.system_structure() as ssd:
            assert ssd.system is not None
            sources = {element.name: element.source for element in ssd.system.elements}
    assert sources["source"] == "resources/Sine.fmu"


def test_resolve_rejects_an_unknown_key(tmp_path: Path) -> None:
    _, architecture = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)

    with pytest.raises(ValueError, match="Unknown selection key 'missing'"):
        resolve(architecture, "System", {"missing": "stepImplementation"})


def test_resolve_accepts_a_dotted_path_for_nesting(tmp_path: Path) -> None:
    """A nested variation point is selected by its dotted usage path."""
    _, architecture = _load_architecture(tmp_path, NESTED_VARIATION)

    resolved = resolve(architecture, "System", {"inner.source": "a"})

    assert resolved.part_definitions["Inner"].parts["source"].type_name == "A"


def test_resolve_rejects_an_ambiguous_bare_key(tmp_path: Path) -> None:
    _, architecture = _load_architecture(tmp_path, AMBIGUOUS_NAMES)

    with pytest.raises(
        ValueError,
        match="Selection key 'x' is ambiguous.*'x', 'inner.x'",
    ):
        resolve(architecture, "System", {"x": "anything"})


def test_resolve_rejects_a_non_variation_usage(tmp_path: Path) -> None:
    _, architecture = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)

    with pytest.raises(
        ValueError,
        match="'gain', which is not a variation point",
    ):
        resolve(architecture, "System", {"gain": "stepImplementation"})


def test_resolve_rejects_an_unknown_variant(tmp_path: Path) -> None:
    _, architecture = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)

    with pytest.raises(
        ValueError,
        match="Unknown variant 'nope' for variation point 'SourceChoice'",
    ):
        resolve(architecture, "System", {"source": "nope"})


def test_resolve_rejects_an_unselected_variation_point(tmp_path: Path) -> None:
    _, architecture = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)

    with pytest.raises(
        ValueError,
        match="Variation point 'SourceChoice' at 'source'.*is not selected",
    ):
        resolve(architecture, "System", {})


def test_resolve_substitutes_a_usage_level_variant(tmp_path: Path) -> None:
    """A usage-level point is selected by its usage path and keeps the name."""
    _, architecture = _load_architecture(tmp_path, USAGE_VARIATION)

    resolved = resolve(architecture, "System", {"source": "stepSource"})

    source = resolved.part_definitions["System"].parts["source"]
    assert source.type_name == "Step"
    assert source.name == "source"
    assert source.is_variation is False


def test_resolve_synthesises_a_body_variant(tmp_path: Path) -> None:
    """A body variant becomes a definition carrying the point's ports."""
    _, architecture = _load_architecture(tmp_path, BODY_VARIATION)

    resolved = resolve(architecture, "System", {"path": "directPath"})

    usage = resolved.part_definitions["System"].parts["path"]
    assert usage.type_name == "PathChoice__directPath"
    definition = resolved.part_definitions[usage.type_name]
    assert list(definition.ports) == ["u", "y"]
    assert list(definition.parts) == ["gain"]
    assert [conn.key for conn in definition.connections.values()] == [
        "u->gain.u",
        "gain.y->y",
    ]
    assert architecture.part_definitions["System"].parts["path"].type_name == (
        "PathChoice"
    )


def _ssd_tree(system) -> dict:
    """Name, nested elements, and connections of one SSD system."""
    elements = [
        _ssd_tree(element) if hasattr(element, "elements") else {
            "name": element.name,
            "source": element.source,
        }
        for element in system.elements
    ]
    return {
        "name": system.name,
        "elements": elements,
        "connections": [
            (
                connection.start_element,
                connection.start_connector,
                connection.end_element,
                connection.end_connector,
            )
            for connection in system.connections
        ],
    }


def _generated_ssd_tree(output: Path) -> dict:
    with SSD(output, mode="r") as ssd:
        assert ssd.system is not None
        return _ssd_tree(ssd.system)


def test_example_03_selects_a_usage_level_variant(tmp_path: Path) -> None:
    """Example 03: the point sits on the usage, the SSD name stays 'source'."""
    path, architecture = _load_architecture(tmp_path, USAGE_LEVEL_VARIATION)

    source = architecture.part_definitions["System"].parts["source"]
    assert source.is_variation is True
    assert [(variant.name, variant.type_name) for variant in source.variants] == [
        ("stepSource", "Step"),
        ("sineSource", "Sine"),
    ]

    sources = {}
    for variant in ("stepSource", "sineSource"):
        output = generate_ssd(
            path,
            tmp_path / "out" / f"{variant}.ssd",
            "System",
            selections={"source": variant},
        )
        sources[variant] = _component_sources(output)["source"]
    assert sources == {
        "stepSource": "resources/Step.fmu",
        "sineSource": "resources/Sine.fmu",
    }


def test_example_08_path_variants_differ_in_nested_structure(
    tmp_path: Path,
) -> None:
    """Example 08: each body yields a subsystem with its own decomposition."""
    path, _ = _load_architecture(tmp_path, CONNECTION_VARIATION)

    direct = _generated_ssd_tree(
        generate_ssd(
            path,
            tmp_path / "out" / "direct.ssd",
            "System",
            selections={"path": "directPath"},
        )
    )
    filtered = _generated_ssd_tree(
        generate_ssd(
            path,
            tmp_path / "out" / "filtered.ssd",
            "System",
            selections={"path": "filteredPath"},
        )
    )

    assert direct["elements"][1] == {
        "name": "path",
        "elements": [{"name": "gain", "source": "resources/Gain.fmu"}],
        "connections": [
            (None, "u", "gain", "u"),
            ("gain", "y", None, "y"),
        ],
    }
    assert filtered["elements"][1] == {
        "name": "path",
        "elements": [
            {"name": "firstStage", "source": "resources/Gain.fmu"},
            {"name": "gain", "source": "resources/Gain.fmu"},
        ],
        "connections": [
            (None, "u", "firstStage", "u"),
            ("firstStage", "y", "gain", "u"),
            ("gain", "y", None, "y"),
        ],
    }
    assert direct["connections"] == filtered["connections"]


def test_example_08_filtered_build_is_byte_identical(tmp_path: Path) -> None:
    """The same selection twice produces the same SSD bytes."""
    path, _ = _load_architecture(tmp_path, CONNECTION_VARIATION)

    written = [
        generate_ssd(
            path,
            tmp_path / f"filtered-{index}.ssd",
            "System",
            selections={"path": "filteredPath"},
        ).read_bytes()
        for index in range(2)
    ]
    assert written[0] == written[1]


def test_example_08_rejects_an_unselected_body_point(tmp_path: Path) -> None:
    _, architecture = _load_architecture(tmp_path, CONNECTION_VARIATION)

    with pytest.raises(
        ValueError,
        match="Variation point 'PathChoice' at 'path'.*is not selected",
    ):
        resolve(architecture, "System", {})


UNDECLARED_BODY_PORT = fixture_text("variation/undeclared-body-port.sysml")


def test_resolve_rejects_a_body_port_the_point_does_not_declare(
    tmp_path: Path,
) -> None:
    _, architecture = _load_architecture(tmp_path, UNDECLARED_BODY_PORT)

    with pytest.raises(
        ValueError,
        match="Variant 'directPath' of variation point 'PathChoice' connects to "
        "port 'missing', which the point does not declare",
    ):
        resolve(architecture, "System", {"path": "directPath"})


def test_example_09_captures_body_attributes_and_bindings(tmp_path: Path) -> None:
    """Example 09: a statement body carries a set usage and its binds."""
    _, architecture = _load_architecture(tmp_path, PARAMETER_BINDING_VARIATION)

    usage = architecture.part_definitions["test_selected"].parts["parameters"]
    body = usage.variants[1].body
    assert body is not None
    assert list(body.attributes) == ["values"]
    assert body.attributes["values"].type_name == "LateStepValues"
    assert [binding.key for binding in body.bindings] == [
        "sut.step.parameters.height=values.height",
        "sut.step.parameters.offset=values.offset",
        "sut.step.parameters.startTime=values.startTime",
        "sut.gain.parameters.k=values.k",
    ]


def test_example_09_selected_body_merges_into_the_analysis(
    tmp_path: Path,
) -> None:
    """Selection adds the set usage and binds to the analysis, not a component."""
    _, architecture = _load_architecture(tmp_path, PARAMETER_BINDING_VARIATION)

    resolved = resolve(
        architecture, "test_selected", {"parameters": "lateStepBinding"}
    )
    analysis = resolved.part_definitions["test_selected"]
    assert "parameters" not in analysis.parts
    assert analysis.attributes["values"].type_name == "LateStepValues"
    assert [binding.key for binding in analysis.bindings] == [
        "sut.step.parameters.height=values.height",
        "sut.step.parameters.offset=values.offset",
        "sut.step.parameters.startTime=values.startTime",
        "sut.gain.parameters.k=values.k",
    ]
    assert architecture.part_definitions["test_selected"].bindings == []
    assert architecture.part_definitions["test_selected"].parts[
        "parameters"
    ].is_variation


@pytest.mark.parametrize(
    ("variant", "expected"),
    [
        (
            "baselineBinding",
            {"height": 2.0, "offset": 1.0, "startTime": 0.25, "k": 3.0},
        ),
        (
            "lateStepBinding",
            {"height": 2.0, "offset": 1.0, "startTime": 0.75, "k": 3.0},
        ),
        (
            "highGainBinding",
            {"height": 2.0, "offset": 1.0, "startTime": 0.25, "k": 9.0},
        ),
    ],
)
def test_example_09_analysis_selection_writes_the_body_set(
    tmp_path: Path, variant: str, expected: dict[str, float]
) -> None:
    """The merged set usage becomes the SSV behind the analysis."""
    path, _ = _load_architecture(tmp_path, PARAMETER_BINDING_VARIATION)

    artifacts = generate_analysis(
        path,
        tmp_path / "analysis",
        "test_selected",
        model_name="System",
        selections={"parameters": variant},
    )

    assert artifacts.ssv is not None
    assert _ssv_values(artifacts.ssv) == expected
    ssm = artifacts.ssm.read_text(encoding="utf-8")
    assert 'target="step.height"' in ssm
    assert 'target="gain.k"' in ssm


def test_example_09_analysis_ssd_equals_the_fixed_topology_ssd(
    tmp_path: Path,
) -> None:
    """The statement container never reaches the SSD; bytes stay fixed."""
    path, architecture = _load_architecture(tmp_path, PARAMETER_BINDING_VARIATION)

    fixed = generate_ssd(path, tmp_path / "fixed.ssd", "System")
    resolved = resolve(
        architecture, "test_selected", {"parameters": "lateStepBinding"}
    )
    selected = tmp_path / "selected.ssd"
    with SSD(selected, mode="w") as ssd:
        build_ssd(ssd, resolved.get_part_def("System"), resolved)

    assert selected.read_bytes() == fixed.read_bytes()


def test_example_10_captures_the_inner_variation_usage(tmp_path: Path) -> None:
    """Example 10: a body's variation usage keeps its flag and its variants."""
    _, architecture = _load_architecture(tmp_path, NESTED_BODY_VARIATION)

    body = architecture.part_definitions["PathChoice"].variants[1].body
    assert body is not None
    stage = body.parts["stage"]
    assert stage.is_variation is True
    assert stage.type_name == "StageChoice"
    assert [(variant.name, variant.type_name) for variant in stage.variants] == [
        ("gainStage", "Gain"),
        ("attenuateStage", "Attenuate"),
    ]


def test_example_10_dotted_selection_resolves_both_points(
    tmp_path: Path,
) -> None:
    """The inner key extends the outer usage path with a dot."""
    path, architecture = _load_architecture(tmp_path, NESTED_BODY_VARIATION)

    resolved = resolve(
        architecture,
        "System",
        {"path": "nestedPath", "path.stage": "attenuateStage"},
    )
    part = resolved.part_definitions["System"].parts["path"]
    assert part.type_name == "PathChoice__nestedPath"
    definition = resolved.part_definitions[part.type_name]
    assert list(definition.parts) == ["stage", "gain"]
    assert definition.parts["stage"].type_name == "Attenuate"

    tree = _generated_ssd_tree(
        generate_ssd(
            path,
            tmp_path / "nested.ssd",
            "System",
            selections={"path": "nestedPath", "path.stage": "attenuateStage"},
        )
    )
    assert tree["elements"][1] == {
        "name": "path",
        "elements": [
            {"name": "stage", "source": "resources/Attenuate.fmu"},
            {"name": "gain", "source": "resources/Gain.fmu"},
        ],
        "connections": [
            (None, "u", "stage", "u"),
            ("stage", "y", "gain", "u"),
            ("gain", "y", None, "y"),
        ],
    }


def test_example_10_unselected_inner_point_names_the_full_path(
    tmp_path: Path,
) -> None:
    """An inner point left unselected fails with its dotted path."""
    _, architecture = _load_architecture(tmp_path, NESTED_BODY_VARIATION)

    with pytest.raises(
        ValueError,
        match="Variation point 'StageChoice' at 'path.stage'.*is not selected",
    ):
        resolve(architecture, "System", {"path": "nestedPath"})


def test_example_10_inner_key_needs_the_outer_body_first(
    tmp_path: Path,
) -> None:
    """Without the outer selection the inner usage does not exist yet."""
    _, architecture = _load_architecture(tmp_path, NESTED_BODY_VARIATION)

    with pytest.raises(ValueError, match="Unknown selection key 'path.stage'"):
        resolve(architecture, "System", {"path.stage": "attenuateStage"})


THREE_LEVELS = fixture_text("variation/three-levels.sysml")


def test_three_level_variation_is_rejected_not_flattened(tmp_path: Path) -> None:
    _, architecture = _load_architecture(tmp_path, THREE_LEVELS)

    with pytest.raises(
        ValueError,
        match="variation nested deeper than two levels is not supported",
    ):
        resolve(
            architecture,
            "System",
            {"path": "nestedPath", "path.stage": "deepStage"},
        )


VALUED_BODY_ATTRIBUTE = fixture_text("variation/valued-body-attribute.sysml")


def test_variant_body_rejects_an_attribute_value_it_cannot_carry(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError, match="body attributes carry a type only"
    ):
        _load_architecture(tmp_path, VALUED_BODY_ATTRIBUTE)


def test_parse_selections_rejects_a_malformed_value() -> None:
    with pytest.raises(ValueError, match="expected KEY=VARIANT"):
        _parse_selections(["source"])


def test_cli_generate_ssd_selects_a_variant(tmp_path: Path) -> None:
    """`pyssp generate ssd --select source=...` writes the selected variant."""
    path, _ = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)
    output = tmp_path / "out" / "SystemStructure.ssd"

    code = main(
        [
            "generate",
            "ssd",
            "--architecture",
            str(path),
            "--composition",
            "System",
            "--output",
            str(output),
            "--select",
            "source=stepImplementation",
        ]
    )

    assert code == 0
    assert _component_sources(output)["source"] == "resources/Step.fmu"


def test_cli_generate_ssd_reports_a_malformed_selection(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path, _ = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)

    code = main(
        [
            "generate",
            "ssd",
            "--architecture",
            str(path),
            "--composition",
            "System",
            "--select",
            "source",
        ]
    )

    assert code == 1
    assert "[error] Invalid --select value 'source'" in capsys.readouterr().out


ATTRIBUTE_VARIATION = fixture_text("variation/attribute-variation.sysml")


def test_has_variation_covers_definitions_usages_and_attributes(
    tmp_path: Path,
) -> None:
    _, definition = _load_architecture(tmp_path / "definition", DEFINITION_VARIATION)
    _, usage = _load_architecture(tmp_path / "usage", USAGE_VARIATION)
    _, attribute = _load_architecture(tmp_path / "attribute", ATTRIBUTE_VARIATION)
    _, clean = _load_architecture(tmp_path / "clean", NO_VARIATION)

    assert has_variation(definition) is True
    assert has_variation(usage) is True
    assert has_variation(attribute) is True
    assert has_variation(clean) is False


def test_generate_ssp_records_selection_deterministically(tmp_path: Path) -> None:
    """A selected build carries a byte-stable selection record in extra/."""
    path, _ = _load_architecture(tmp_path, DEFINITION_VARIATION)

    first = generate_ssp(
        path,
        tmp_path / "one.ssp",
        "System",
        selections={"source": "stepImplementation"},
    )
    second = generate_ssp(
        path,
        tmp_path / "two.ssp",
        "System",
        selections={"source": "stepImplementation"},
    )

    with zipfile.ZipFile(first) as archive:
        assert json.loads(
            archive.read("extra/org.pyssp/selection.json")
        ) == {
            "composition": "System",
            "selections": {"source": "stepImplementation"},
        }
    assert first.read_bytes() == second.read_bytes()


def test_generate_ssp_records_the_configuration_that_produced_the_selection(
    tmp_path: Path,
) -> None:
    """The provenance names the configuration and stays byte-identical."""
    path, _ = _load_architecture(tmp_path, DEFINITION_VARIATION)
    arguments = {
        "selections": {"source": "stepImplementation"},
        "configuration": "StepSystem",
    }

    first = generate_ssp(path, tmp_path / "one.ssp", "System", **arguments)
    second = generate_ssp(path, tmp_path / "two.ssp", "System", **arguments)

    with zipfile.ZipFile(first) as archive:
        assert json.loads(
            archive.read("extra/org.pyssp/selection.json")
        ) == {
            "composition": "System",
            "configuration": "StepSystem",
            "selections": {"source": "stepImplementation"},
        }
    assert first.read_bytes() == second.read_bytes()


def test_generate_ssp_omits_an_absent_or_empty_configuration(
    tmp_path: Path,
) -> None:
    """No configuration and an empty one write the same record as before."""
    path, _ = _load_architecture(tmp_path, DEFINITION_VARIATION)

    for index, configuration in enumerate((None, "")):
        output = generate_ssp(
            path,
            tmp_path / f"{index}.ssp",
            "System",
            selections={"source": "stepImplementation"},
            configuration=configuration,
        )
        with zipfile.ZipFile(output) as archive:
            record = json.loads(
                archive.read("extra/org.pyssp/selection.json")
            )
        assert record == {
            "composition": "System",
            "selections": {"source": "stepImplementation"},
        }


def test_generate_ssp_without_selection_adds_no_provenance(
    tmp_path: Path,
) -> None:
    path, _ = _load_architecture(tmp_path, NO_VARIATION)

    output = generate_ssp(path, tmp_path / "plain.ssp", "System")

    with zipfile.ZipFile(output) as archive:
        assert not [
            name for name in archive.namelist() if name.startswith("extra/")
        ]


def test_generate_sysml_refuses_to_overwrite_variation(tmp_path: Path) -> None:
    target = tmp_path / "authored.sysml"
    write_model(target, DEFINITION_VARIATION)
    ssd_path = write_bootstrap_ssd(tmp_path / "in.ssd", "System")

    with pytest.raises(
        ValueError,
        match="SysML export does not represent variation points.*SourceChoice",
    ):
        generate_sysml_from_ssd(ssd_path, target)

    assert "variation part def SourceChoice" in target.read_text()


def test_sync_refuses_to_rewrite_variation(tmp_path: Path) -> None:
    path, _ = _load_architecture(tmp_path / "arch", DEFINITION_VARIATION)
    ssd_path = write_bootstrap_ssd(tmp_path / "in.ssd", "System")

    with pytest.raises(
        ValueError,
        match="SysML export does not represent variation points.*SourceChoice",
    ):
        sync_sysml_from_ssd(path, ssd_path, "System")


ATTRIBUTE_SET_VARIATION = fixture_text("variation/attribute-set-variation.sysml")


def _ssv_values(path: Path) -> dict[str, float]:
    with SSV(path, mode="r") as ssv:
        return {
            name: float(parameter.attributes["value"])
            for name, parameter in ssv.parameters_by_name().items()
        }


def test_attribute_variation_captures_variants(tmp_path: Path) -> None:
    """A variation attribute def keeps variant attribute members, not attributes."""
    _, architecture = _load_architecture(tmp_path, ATTRIBUTE_SET_VARIATION)

    choice = architecture.attribute_definitions["ScenarioChoice"]
    assert choice.is_variation is True
    assert [
        (variant.name, variant.kind, variant.type_name)
        for variant in choice.variants
    ] == [
        ("baseline", "attribute", "BaselineScenario"),
        ("lateStep", "attribute", "LateStepScenario"),
        ("highGain", "attribute", "HighGainScenario"),
    ]
    assert choice.attributes == {}


def test_resolve_substitutes_the_attribute_usage_type(tmp_path: Path) -> None:
    """Resolution rewrites the attribute usage type on a copy."""
    _, architecture = _load_architecture(tmp_path, ATTRIBUTE_SET_VARIATION)

    resolved = resolve(architecture, "test_selected_scenario", {"scenario": "baseline"})

    assert (
        resolved.part_definitions["test_selected_scenario"]
        .attributes["scenario"]
        .type_name
    ) == "BaselineScenario"
    assert (
        architecture.part_definitions["test_selected_scenario"]
        .attributes["scenario"]
        .type_name
    ) == "ScenarioChoice"


def test_resolve_finds_an_analysis_attribute_from_the_model(tmp_path: Path) -> None:
    """A composing analysis's attribute usage is selectable when its model is resolved."""
    _, architecture = _load_architecture(tmp_path, ATTRIBUTE_SET_VARIATION)

    resolved = resolve(architecture, "System", {"scenario": "lateStep"})

    assert (
        resolved.part_definitions["test_selected_scenario"]
        .attributes["scenario"]
        .type_name
    ) == "LateStepScenario"


@pytest.mark.parametrize(
    ("variant", "expected"),
    [
        ("baseline", "BaselineScenario"),
        ("lateStep", "LateStepScenario"),
        ("highGain", "HighGainScenario"),
    ],
)
def test_every_attribute_variant_resolves(
    tmp_path: Path, variant: str, expected: str
) -> None:
    _, architecture = _load_architecture(tmp_path, ATTRIBUTE_SET_VARIATION)

    resolved = resolve(architecture, "test_selected_scenario", {"scenario": variant})

    assert (
        resolved.part_definitions["test_selected_scenario"]
        .attributes["scenario"]
        .type_name
    ) == expected


@pytest.mark.parametrize(
    ("variant", "expected"),
    [
        (
            "baseline",
            {"height": 2.0, "offset": 1.0, "startTime": 0.25, "k": 3.0},
        ),
        (
            "lateStep",
            {"height": 2.0, "offset": 1.0, "startTime": 0.75, "k": 3.0},
        ),
        (
            "highGain",
            {"height": 2.0, "offset": 1.0, "startTime": 0.25, "k": 9.0},
        ),
    ],
)
def test_generate_analysis_writes_the_selected_attribute_set(
    tmp_path: Path, variant: str, expected: dict[str, float]
) -> None:
    """The selected variant becomes the set definition behind the analysis SSV."""
    path, _ = _load_architecture(tmp_path, ATTRIBUTE_SET_VARIATION)

    artifacts = generate_analysis(
        path,
        tmp_path / "analysis",
        "test_selected_scenario",
        model_name="System",
        selections={"scenario": variant},
    )

    assert _ssv_values(artifacts.ssv) == expected
    ssm = artifacts.ssm.read_text(encoding="utf-8")
    assert 'target="step.height"' in ssm
    assert 'target="gain.k"' in ssm


def test_generate_ssd_is_identical_across_attribute_selections(
    tmp_path: Path,
) -> None:
    """Attribute selection changes values only; the SSD bytes do not move."""
    path, _ = _load_architecture(tmp_path, ATTRIBUTE_SET_VARIATION)

    written = [
        generate_ssd(
            path,
            tmp_path / f"{variant}.ssd",
            "System",
            selections={"scenario": variant},
        ).read_bytes()
        for variant in ("baseline", "lateStep", "highGain")
    ]

    assert len(set(written)) == 1


def test_generate_ssd_does_not_require_an_analysis_attribute_point(
    tmp_path: Path,
) -> None:
    """A model build is not blocked by another analysis's scenario point."""
    path, _ = _load_architecture(tmp_path, ATTRIBUTE_SET_VARIATION)

    generate_ssd(path, tmp_path / "out" / "SystemStructure.ssd", "System")

    assert (tmp_path / "out" / "SystemStructure.ssd").is_file()


def test_generate_analysis_rejects_an_unselected_attribute_point(tmp_path: Path) -> None:
    path, _ = _load_architecture(tmp_path, ATTRIBUTE_SET_VARIATION)

    with pytest.raises(
        ValueError,
        match=(
            "variation point 'ScenarioChoice' at 'scenario' is not selected; "
            "bind it in analysis 'test_selected_scenario'"
        ),
    ):
        generate_analysis(
            path,
            tmp_path / "analysis",
            "test_selected_scenario",
            model_name="System",
        )


def test_resolve_rejects_an_unknown_attribute_key(tmp_path: Path) -> None:
    _, architecture = _load_architecture(tmp_path, ATTRIBUTE_SET_VARIATION)

    with pytest.raises(ValueError, match="Unknown selection key 'missing'"):
        resolve(architecture, "test_selected_scenario", {"missing": "baseline"})


def test_resolve_rejects_a_non_variation_attribute_usage(tmp_path: Path) -> None:
    _, architecture = _load_architecture(tmp_path, ATTRIBUTE_SET_VARIATION)

    with pytest.raises(
        ValueError,
        match="names attribute usage 'experiment_baseline', which is not a "
        "variation point",
    ):
        resolve(
            architecture,
            "test_selected_scenario",
            {"experiment_baseline": "baseline"},
        )


def test_resolve_rejects_an_unknown_attribute_variant(tmp_path: Path) -> None:
    _, architecture = _load_architecture(tmp_path, ATTRIBUTE_SET_VARIATION)

    with pytest.raises(
        ValueError,
        match="Unknown variant 'nope' for variation point 'ScenarioChoice'",
    ):
        resolve(architecture, "test_selected_scenario", {"scenario": "nope"})


def test_resolve_rejects_an_unselected_attribute_point(tmp_path: Path) -> None:
    _, architecture = _load_architecture(tmp_path, ATTRIBUTE_SET_VARIATION)

    with pytest.raises(
        ValueError,
        match="Attribute variation point 'ScenarioChoice' at 'scenario'.*"
        "is not selected",
    ):
        resolve(architecture, "test_selected_scenario", {})


UNTYPED_ATTRIBUTE_VARIANT = fixture_text("variation/untyped-attribute-variant.sysml")


def test_resolve_rejects_an_attribute_variant_without_a_type(tmp_path: Path) -> None:
    _, architecture = _load_architecture(tmp_path, UNTYPED_ATTRIBUTE_VARIANT)

    with pytest.raises(
        ValueError,
        match="'empty' of variation point 'Choice' has no resolvable type",
    ):
        resolve(architecture, "System", {"value": "empty"})


def test_parse_selections_rejects_a_duplicate_key() -> None:
    with pytest.raises(ValueError, match="Duplicate selection for 'scenario'"):
        _parse_selections(["scenario=baseline", "scenario=lateStep"])


def test_cli_generate_analysis_selects_an_attribute_variant(tmp_path: Path) -> None:
    """`pyssp generate analysis --select scenario=...` writes that set's SSV."""
    path, _ = _load_architecture(tmp_path, ATTRIBUTE_SET_VARIATION)
    output = tmp_path / "analysis"

    code = main(
        [
            "generate",
            "analysis",
            "--architecture",
            str(path),
            "--composition",
            "test_selected_scenario",
            "--output-dir",
            str(output),
            "--model",
            "System",
            "--select",
            "scenario=highGain",
        ]
    )

    assert code == 0
    assert _ssv_values(output / "HighGainScenario.ssv")["k"] == 9.0
