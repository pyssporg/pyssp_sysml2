"""Constraint export round trip: repo model → SysML text → repo model."""

from __future__ import annotations

from pyssp_sysml2.model import load
from tests.fixture_files import fixture_text
from tests.testhelpers import write_model


def test_export_preserves_constraint_definitions_and_usages(tmp_path) -> None:
    source = tmp_path / "constraints.sysml"
    write_model(source, fixture_text("constraints/constraints.sysml"))
    architecture = load(source)

    exported = architecture.export_declared()["constraints.sysml"]

    assert "constraint def SineRequiresSingleStage {" in exported
    assert (
        "chosenSource == SourceChoice::sineImplementation"
        " implies chosenGain == GainChoice::singleStage"
    ) in exported
    assert "constraint requiresSingleStage : SineRequiresSingleStage {" in exported
    assert "in chosenSource = source;" in exported
    assert "in chosenGain = gain;" in exported
    assert "assert requiresSingleStage;" in exported

    reloaded_path = tmp_path / "round-trip.sysml"
    write_model(reloaded_path, exported)
    reloaded = load(reloaded_path)

    original_definition = architecture.get_constraint_def("SineRequiresSingleStage")
    reloaded_definition = reloaded.get_constraint_def("SineRequiresSingleStage")
    assert reloaded_definition.expression == original_definition.expression

    original_usages = {
        usage.name: usage
        for usage in architecture.get_part_def("ConstrainedComposition").constraints
    }
    reloaded_usages = {
        usage.name: usage
        for usage in reloaded.get_part_def("ConstrainedComposition").constraints
    }
    assert set(reloaded_usages) == set(original_usages)
    for name, usage in original_usages.items():
        assert reloaded_usages[name].type_name == usage.type_name
        assert reloaded_usages[name].bindings == usage.bindings
        assert reloaded_usages[name].asserted == usage.asserted
        assert reloaded_usages[name].negated == usage.negated


def test_export_preserves_negated_assert(tmp_path) -> None:
    source = tmp_path / "negated.sysml"
    write_model(source, fixture_text("constraints/negated.sysml"))
    architecture = load(source)

    exported = architecture.export_declared()["negated.sysml"]

    assert "assert not mustBeOff;" in exported
    assert "assert mustBeOff;" not in exported

    reloaded_path = tmp_path / "round-trip.sysml"
    write_model(reloaded_path, exported)
    reloaded = load(reloaded_path)

    usage = reloaded.get_part_def("NegatedComposition").constraints[0]
    assert usage.name == "mustBeOff"
    assert usage.asserted is True
    assert usage.negated is True
