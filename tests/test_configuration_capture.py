"""Model-level configuration capture: ``:>>``, ``:>``, feature values, bodies."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyssp_sysml2.model import load
from pyssp_sysml2.model.variation import variation_facts
from tests.fixture_files import fixture_text
from tests.testhelpers import write_model


def _load_configuration(tmp_path: Path, name: str = "configuration"):
    path = tmp_path / name / "configuration.sysml"
    write_model(path, fixture_text("configuration/configuration.sysml"))
    return path, load(path)


def _load_fixture(tmp_path: Path, name: str):
    """Write and load one committed ``configuration/`` document."""
    path = tmp_path / name.removesuffix(".sysml") / name
    write_model(path, fixture_text(f"configuration/{name}"))
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

    # The reloaded usages are the same dataclasses, not merely similar text.
    assert source == architecture.part_definitions["StepSystem"].parts["source"]
    assert scenario == (
        architecture.part_definitions["nominalRedefined"].attributes["scenario"]
    )


# -- capture shape: values and subsettings ------------------------------------


def test_qualified_and_local_feature_values_are_kept_verbatim(tmp_path: Path) -> None:
    """``= SourceChoice::step`` and ``= qualified`` both reach ``value``."""
    _, architecture = _load_fixture(tmp_path, "values.sysml")
    parts = architecture.part_definitions["ValueForms"].parts

    qualified = parts["qualified"]
    assert qualified.redefines == ("qualified",)
    assert qualified.subsets == ()
    assert qualified.value == "SourceChoice::step"
    assert qualified.type_name is None
    assert qualified.body is None

    local = parts["local"]
    assert local.redefines == ("local",)
    assert local.subsets == ()
    assert local.value == "qualified"


def test_subsetting_usage_without_a_body_has_no_body(tmp_path: Path) -> None:
    """``part choice :> PathChoice::nestedPath;`` keeps only its subsetting."""
    _, architecture = _load_fixture(tmp_path, "values.sysml")
    choice = architecture.part_definitions["ValueForms"].parts["choice"]

    assert choice.subsets == ("PathChoice::nestedPath",)
    assert choice.redefines == ()
    assert choice.value is None
    assert choice.type_name is None
    assert choice.body is None


def test_redefinition_subsetting_and_value_are_all_kept(tmp_path: Path) -> None:
    """A usage may carry ``:>>``, ``:>``, and ``=`` in one declaration."""
    _, architecture = _load_fixture(tmp_path, "values.sysml")
    combined = architecture.part_definitions["ValueForms"].parts["combined"]

    assert combined.redefines == ("combined",)
    assert combined.subsets == ("PathChoice::nestedPath",)
    assert combined.value == "SourceChoice::step"
    assert combined.type_name is None
    assert combined.body is None


def test_two_redefinition_targets_are_skipped_not_guessed(tmp_path: Path) -> None:
    """``part :>> alpha, beta`` names nothing, so its extras are skipped."""
    text = fixture_text("configuration/values.sysml")
    facts = variation_facts(text)
    assert not [key for key in facts.usage_extras if key[0] == "Ambiguous"]

    _, architecture = _load_fixture(tmp_path, "values.sysml")
    parts = architecture.part_definitions["Ambiguous"].parts
    assert len(parts) == 1
    ambiguous = next(iter(parts.values()))
    assert ambiguous.redefines == ()
    assert ambiguous.subsets == ()
    assert ambiguous.value is None


# -- capture shape: bodies ----------------------------------------------------


def test_body_nests_two_levels_of_redefinition_named_parts(
    tmp_path: Path,
) -> None:
    """``part :>> outer { part :>> middle { ... } }`` recurses into each body."""
    _, architecture = _load_fixture(tmp_path, "bodies.sysml")
    outer = architecture.part_definitions["TwoLevels"].parts["outer"]

    assert outer.redefines == ("outer",)
    assert outer.body is not None
    assert list(outer.body.parts) == ["middle"]

    middle = outer.body.parts["middle"]
    assert middle.redefines == ("middle",)
    assert middle.body is not None
    assert list(middle.body.parts) == ["inner"]

    inner = middle.body.parts["inner"]
    assert inner.redefines == ("inner",)
    assert inner.body is None


def test_unnamed_body_part_takes_its_single_redefinition_target(
    tmp_path: Path,
) -> None:
    """``part :>> bound`` inside a body is keyed by ``bound`` (name fallback)."""
    _, architecture = _load_fixture(tmp_path, "bodies.sysml")
    body = architecture.part_definitions["Renamed"].parts["holder"].body

    assert body is not None
    assert list(body.parts) == ["bound"]
    bound = body.parts["bound"]
    assert (bound.name, bound.redefines, bound.type_name) == (
        "bound",
        ("bound",),
        "System",
    )
    assert bound.body is None


def test_body_keeps_its_parts_connection_and_binding(tmp_path: Path) -> None:
    """A body carries parts, a ``connect``, and a ``bind`` without dropping any."""
    _, architecture = _load_fixture(tmp_path, "bodies.sysml")
    body = architecture.part_definitions["Wired"].parts["src"].body

    assert body is not None
    assert list(body.parts) == ["a", "b"]
    assert [part.type_name for part in body.parts.values()] == ["Gain", "Gain"]

    assert list(body.connections) == ["a.y->b.u"]
    connection = body.connections["a.y->b.u"]
    assert (
        connection.source_part,
        connection.source_port,
        connection.destination_part,
        connection.destination_port,
    ) == ("a", "y", "b", "u")

    assert [(binding.source, binding.target) for binding in body.bindings] == [
        (("a", "x"), ("b", "y"))
    ]


def test_body_keeps_a_redefining_and_a_plain_attribute(tmp_path: Path) -> None:
    """``attribute :>> mode`` redefines; ``attribute extra`` does not."""
    _, architecture = _load_fixture(tmp_path, "bodies.sysml")
    body = architecture.part_definitions["Wired"].parts["src"].body

    assert body is not None
    mode = body.attributes["mode"]
    assert (mode.name, mode.redefines, mode.type_name) == (
        "mode",
        ("mode",),
        "Integer",
    )
    extra = body.attributes["extra"]
    assert (extra.name, extra.redefines, extra.type_name) == (
        "extra",
        (),
        "Integer",
    )


# -- export contract ----------------------------------------------------------


def test_export_orders_redefinition_subsetting_and_value(tmp_path: Path) -> None:
    """``:>> name``, ``:> Type::variant``, then ``= value``, and reload equality."""
    _, architecture = _load_fixture(tmp_path, "values.sysml")
    text = architecture.export_declared()["values.sysml"]

    assert (
        "    part :>> combined :> PathChoice::nestedPath "
        "= SourceChoice::step;" in text
    )
    assert "    part :>> qualified = SourceChoice::step;" in text
    assert "    part :>> local = qualified;" in text
    assert "    part choice :> PathChoice::nestedPath;" in text

    reloaded_path = tmp_path / "values-roundtrip" / "values.sysml"
    write_model(reloaded_path, text)
    reloaded = load(reloaded_path)

    original = architecture.part_definitions["ValueForms"].parts
    round_tripped = reloaded.part_definitions["ValueForms"].parts
    assert round_tripped == original
    combined = round_tripped["combined"]
    assert (combined.redefines, combined.subsets, combined.value) == (
        ("combined",),
        ("PathChoice::nestedPath",),
        "SourceChoice::step",
    )


# -- capture errors -----------------------------------------------------------


def test_unsupported_member_in_a_configuration_body_is_refused(
    tmp_path: Path,
) -> None:
    """A ``port`` inside a configuration body is refused, not dropped."""
    path = tmp_path / "errors" / "unsupported-member.sysml"
    write_model(path, fixture_text("configuration/unsupported-member.sysml"))

    with pytest.raises(ValueError, match="^Unsupported member in a configuration"):
        load(path)


def test_unnamed_body_part_without_one_redefinition_is_refused(
    tmp_path: Path,
) -> None:
    """An anonymous body part with no target has no name to capture."""
    path = tmp_path / "errors" / "unnamed-body-part.sysml"
    write_model(path, fixture_text("configuration/unnamed-body-part.sysml"))

    with pytest.raises(ValueError) as excinfo:
        load(path)
    assert str(excinfo.value) == (
        "A part usage in a configuration body must be named or redefine "
        "exactly one feature"
    )


# -- determinism --------------------------------------------------------------


def test_variation_facts_repeats_identically_for_the_same_text() -> None:
    """Two walks of one text yield equal ``VariationFacts`` (dataclass equality)."""
    text = fixture_text("configuration/bodies.sysml")
    first = variation_facts(text)

    assert first.usage_extras[("Wired", "src")].body is not None
    assert first == variation_facts(text)


def test_export_reload_export_is_byte_identical(tmp_path: Path) -> None:
    """One export canonicalizes; a second cycle emits the same bytes."""
    _, architecture = _load_configuration(tmp_path)
    first = architecture.export_declared()

    reloaded_path = tmp_path / "export-cycle" / "configuration.sysml"
    write_model(reloaded_path, first["configuration.sysml"])
    second = load(reloaded_path).export_declared()

    assert second == first

