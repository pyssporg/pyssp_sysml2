"""Model-level configuration capture: ``:>>``, ``:>``, feature values, bodies."""

from __future__ import annotations

from pathlib import Path

from pyssp_sysml2.model import load
from tests.fixture_files import fixture_text
from tests.testhelpers import write_model


def _load_configuration(tmp_path: Path, name: str = "configuration"):
    path = tmp_path / name / "configuration.sysml"
    write_model(path, fixture_text("configuration/configuration.sysml"))
    return path, load(path)


def test_simple_redefinition_captures_target_and_value(tmp_path: Path) -> None:
    """``part :>> source = SourceChoice::step;`` keeps target, name, and value."""
    _, architecture = _load_configuration(tmp_path)

    source = architecture.part_definitions["StepSystem"].parts["source"]
    assert source.name == "source"
    assert source.redefines == ("source",)
    assert source.value == "SourceChoice::step"
    assert source.type_name is None
    assert source.subsets == ()
    assert source.body is None


def test_subsetting_usage_captures_target_and_body(tmp_path: Path) -> None:
    """``part nestedGainPath :> PathChoice::nestedPath { ... }`` keeps its body."""
    _, architecture = _load_configuration(tmp_path)

    path = architecture.part_definitions["NestedGainSystem"].parts["nestedGainPath"]
    assert path.subsets == ("PathChoice::nestedPath",)
    assert path.redefines == ()
    assert path.type_name is None

    body = path.body
    assert body is not None
    assert list(body.parts) == ["inner_stage", "gain"]
    assert body.parts["gain"].type_name == "Gain"
    nested = body.parts["gain"].body
    assert nested is not None
    assert nested.parts["sub"].type_name == "Step"

    inner = body.parts["inner_stage"]
    assert inner.redefines == ("inner_stage",)
    assert inner.value == "StageChoice::gainStage"

    assert [connection.key for connection in body.connections.values()] == [
        "inner_stage.y->gain.u"
    ]
    assert body.attributes["mode"].redefines == ("mode",)
    assert body.attributes["mode"].type_name == "Integer"


def test_nested_outer_binding_captures_its_value(tmp_path: Path) -> None:
    """``part :>> path = nestedGainPath;`` names the usage after the target."""
    _, architecture = _load_configuration(tmp_path)

    path = architecture.part_definitions["NestedGainSystem"].parts["path"]
    assert path.redefines == ("path",)
    assert path.value == "nestedGainPath"
    assert path.subsets == ()


def test_analysis_attribute_captures_its_declared_type_and_value(
    tmp_path: Path,
) -> None:
    """``attribute scenario : ScenarioChoice = ...`` is a plain typed usage."""
    _, architecture = _load_configuration(tmp_path)

    scenario = architecture.part_definitions["nominal"].attributes["scenario"]
    assert scenario.name == "scenario"
    assert scenario.redefines == ()
    assert scenario.type_name == "ScenarioChoice"
    assert scenario.value == "ScenarioChoice::nominalK3"


def test_redefining_attribute_takes_the_inherited_name(tmp_path: Path) -> None:
    """``attribute :>> scenario = ...`` is named by its redefinition target."""
    _, architecture = _load_configuration(tmp_path)

    scenario = architecture.part_definitions["nominalRedefined"].attributes["scenario"]
    assert scenario.redefines == ("scenario",)
    assert scenario.value == "ScenarioChoice::nominalK3"


def test_exported_configuration_reloads_with_its_bindings(tmp_path: Path) -> None:
    """The exporter re-emits ``:>>``, ``:>``, and the feature value."""
    _, architecture = _load_configuration(tmp_path)

    text = architecture.export_declared()["configuration.sysml"]
    assert "part :>> source = SourceChoice::step;" in text
    assert "part nestedGainPath :> PathChoice::nestedPath;" in text
    assert "part :>> path = nestedGainPath;" in text
    assert "attribute :>> scenario = ScenarioChoice::nominalK3;" in text

    reloaded_path = tmp_path / "roundtrip" / "configuration.sysml"
    write_model(reloaded_path, text)
    reloaded = load(reloaded_path)

    source = reloaded.part_definitions["StepSystem"].parts["source"]
    assert (source.redefines, source.value) == (("source",), "SourceChoice::step")
    path = reloaded.part_definitions["NestedGainSystem"].parts["nestedGainPath"]
    assert (path.subsets, path.redefines) == (("PathChoice::nestedPath",), ())
    scenario = reloaded.part_definitions["nominalRedefined"].attributes["scenario"]
    assert (scenario.redefines, scenario.value) == (
        ("scenario",),
        "ScenarioChoice::nominalK3",
    )
