"""Configuration derivation, CLI selection parsing, and per-analysis plans."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pyssp_sysml2.artifacts.analysis import generate_analysis
from pyssp_sysml2.artifacts.ssd import generate_ssd
from pyssp_sysml2.model import Architecture, load
from pyssp_sysml2.parameters.configuration import (
    configuration_name,
    derived_selection,
    model_root,
)
from pyssp_sysml2.parameters.selection import (
    AnalysisPlan,
    analysis_plans,
    analysis_selection,
    analysis_selections,
    parse_selection,
)
from pyssp_sysml2.parameters.variation import resolve_selected
from tests.fixture_files import fixture_text
from tests.testhelpers import write_model


def _load(tmp_path: Path):
    path = tmp_path / "selection.sysml"
    write_model(path, fixture_text("selection/selection.sysml"))
    return path, load(path)


def _load_text(tmp_path: Path, content: str) -> Architecture:
    path = tmp_path / "configuration.sysml"
    write_model(path, content)
    return load(path)


def _plans(tmp_path: Path):
    _, architecture = _load(tmp_path)
    return {plan.name: plan for plan in analysis_plans(architecture)}


def test_parse_selection_accepts_the_cli_language() -> None:
    assert parse_selection("source=step; path.inner=gain") == {
        "source": "step",
        "path.inner": "gain",
    }
    assert parse_selection("  ") == {}


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("source", "expected 'key=variant'"),
        ("=step", "key and variant must both be non-empty"),
        ("source=", "key and variant must both be non-empty"),
        ("source=step;source=sine", "names variation point 'source' twice"),
    ],
)
def test_parse_selection_rejects_malformed_text(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_selection(text)


def test_model_root_is_the_outermost_composition(tmp_path: Path) -> None:
    _, architecture = _load(tmp_path)

    root = architecture.part_definitions["System"]
    nested = architecture.part_definitions["NestedGainSystem"]

    assert model_root(architecture, root) is root
    assert model_root(architecture, nested) is architecture.part_definitions[
        "PathSystem"
    ]
    assert configuration_name(architecture, "step_single") == "StepSingleSystem"
    assert configuration_name(architecture, "plain") is None


def test_derived_selection_reads_a_simple_configuration(tmp_path: Path) -> None:
    _, architecture = _load(tmp_path)

    assert analysis_selection(architecture, "step_single") == {
        "source": "stepImplementation",
        "gain": "singleStage",
    }


def test_derived_selection_descends_into_nested_points(tmp_path: Path) -> None:
    _, architecture = _load(tmp_path)

    assert derived_selection(architecture, "nested_gain") == {
        "path": "nestedPath",
        "path.inner_stage": "gainStage",
    }


def test_derived_selection_reads_an_analysis_attribute_point(tmp_path: Path) -> None:
    _, architecture = _load(tmp_path)

    assert derived_selection(architecture, "nominal") == {"scenario": "nominalK3"}


def test_derived_selection_is_empty_for_the_plain_root(tmp_path: Path) -> None:
    _, architecture = _load(tmp_path)

    assert derived_selection(architecture, "plain") == {}
    assert analysis_selection(architecture, "plain") == {}


def test_derived_selection_recurses_through_three_levels(tmp_path: Path) -> None:
    architecture = _load_text(tmp_path, fixture_text("selection/deep-nesting.sysml"))

    assert derived_selection(architecture, "deep") == {
        "top": "b",
        "top.inner": "b1",
        "top.inner.deeper": "c1",
    }


def test_derived_selection_rejects_an_unbound_inner_point(tmp_path: Path) -> None:
    _, architecture = _load(tmp_path)

    with pytest.raises(
        ValueError,
        match=(
            "variation point 'StageChoice' at 'path.inner_stage' is not selected; "
            "bind it in configuration 'NestedUnboundSystem'"
        ),
    ):
        derived_selection(architecture, "nested_unbound")


def test_derived_selection_rejects_an_unknown_variant(tmp_path: Path) -> None:
    architecture = _load_text(tmp_path, fixture_text("selection/unknown-variant.sysml"))

    with pytest.raises(
        ValueError,
        match=(
            "Unknown variant 'missing' for variation point 'SourceChoice' at "
            "'source' in configuration 'BadSystem'; expected one of step"
        ),
    ):
        derived_selection(architecture, "bad")


def test_derived_selection_rejects_a_non_point_redefinition(
    tmp_path: Path,
) -> None:
    architecture = _load_text(tmp_path, fixture_text("selection/non-point.sysml"))

    with pytest.raises(
        ValueError,
        match=(
            "redefinition target 'gain' in configuration 'BadSystem' is not a "
            "variation point in 'System'"
        ),
    ):
        derived_selection(architecture, "bad")


def test_plans_classify_legal_violated_and_invalid(tmp_path: Path) -> None:
    plans = _plans(tmp_path)

    assert "Analysis" not in plans, "the role marker is not an analysis"
    assert set(plans) == {
        "step_single",
        "sine_two",
        "broken",
        "nested_gain",
        "nested_unbound",
        "nominal",
        "plain",
    }

    assert plans["step_single"].status == "legal"
    assert plans["step_single"].legal is True
    assert plans["step_single"].configuration == "StepSingleSystem"
    assert plans["step_single"].canonical == {
        "sut.source": "stepImplementation",
        "sut.gain": "singleStage",
    }

    assert plans["nested_gain"].status == "legal"
    assert plans["nested_gain"].configuration == "NestedGainSystem"
    assert plans["nested_gain"].canonical == {
        "sut.path": "nestedPath",
        "sut.path.inner_stage": "gainStage",
    }

    assert plans["nominal"].status == "legal"
    assert plans["nominal"].selection == {"scenario": "nominalK3"}

    assert plans["plain"].status == "legal"
    assert plans["plain"].configuration is None
    assert plans["plain"].selection == {}

    assert plans["sine_two"].status == "violated"
    assert "requiresSingleStage fail" in (plans["sine_two"].detail or "")

    assert plans["broken"].status == "invalid"
    assert "variation point 'SourceChoice' at 'source' is not selected" in (
        plans["broken"].detail or ""
    )
    assert plans["broken"].configuration is None

    assert plans["nested_unbound"].status == "invalid"
    assert (
        "variation point 'StageChoice' at 'path.inner_stage' is not selected"
        in (plans["nested_unbound"].detail or "")
    )
    assert plans["nested_unbound"].configuration == "NestedUnboundSystem"


def test_a_configuration_is_judged_by_its_inherited_assert(
    tmp_path: Path,
) -> None:
    _, architecture = _load(tmp_path)
    plans = {plan.name: plan for plan in analysis_plans(architecture)}

    for name in ("StepSingleSystem", "SineTwoSystem"):
        assert architecture.part_definitions[name].constraints == []
    system = architecture.part_definitions["System"]
    assert [usage.name for usage in system.constraints] == ["requiresSingleStage"]

    assert plans["step_single"].status == "legal"
    assert plans["sine_two"].status == "violated"
    assert "requiresSingleStage fail" in (plans["sine_two"].detail or "")


def test_generate_analysis_scopes_the_configuration_to_the_root(
    tmp_path: Path,
) -> None:
    path, _ = _load(tmp_path)

    artifacts = generate_analysis(
        path,
        tmp_path / "analysis",
        "step_single",
        model_name="selection",
    )

    descriptor = json.loads(artifacts.descriptor.read_text(encoding="utf-8"))
    assert descriptor["composition"] == "System"
    assert descriptor["sut"] == "sut"


def test_generate_analysis_keeps_a_nested_selection(tmp_path: Path) -> None:
    path, _ = _load(tmp_path)

    artifacts = generate_analysis(
        path,
        tmp_path / "analysis",
        "nested_gain",
        model_name="selection",
    )

    descriptor = json.loads(artifacts.descriptor.read_text(encoding="utf-8"))
    assert descriptor["composition"] == "PathSystem"
    _, architecture = _load(tmp_path)
    assert derived_selection(architecture, "nested_gain") == {
        "path": "nestedPath",
        "path.inner_stage": "gainStage",
    }


def test_a_configuration_is_not_a_generation_target(tmp_path: Path) -> None:
    path, _ = _load(tmp_path)

    with pytest.raises(
        ValueError,
        match=(
            "Composition 'NestedGainSystem' is a configuration of 'PathSystem'"
        ),
    ):
        generate_ssd(
            path,
            tmp_path / "out" / "NestedGainSystem.ssd",
            "NestedGainSystem",
            selections={"path": "nestedPath", "path.inner_stage": "gainStage"},
        )


def test_an_explicit_selection_overrides_the_derived_one(tmp_path: Path) -> None:
    path, _ = _load(tmp_path)

    with pytest.raises(ValueError, match="constraint check failed"):
        generate_analysis(
            path,
            tmp_path / "analysis",
            "step_single",
            model_name="selection",
            selections={"source": "sineImplementation", "gain": "twoStages"},
        )


# ---------------------------------------------------------------------------
# Configuration chain shape
# ---------------------------------------------------------------------------


def test_a_definition_specialising_two_ssp_models_is_rejected(
    tmp_path: Path,
) -> None:
    architecture = _load_text(tmp_path, fixture_text("selection/chain-errors.sysml"))

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Definition 'Linear' specialises more than one SspModel definition "
            "(FirstRoot, SecondRoot); a configuration chain must be linear."
        ),
    ):
        derived_selection(architecture, "linear")


def test_a_definition_whose_supertype_is_not_ssp_model_is_rejected(
    tmp_path: Path,
) -> None:
    architecture = _load_text(tmp_path, fixture_text("selection/chain-errors.sysml"))
    orphan = architecture.part_definitions["Orphan"]

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Definition 'Orphan' specialises 'Helper', which is not marked "
            "SspModel; a configuration chain must specialise the root "
            "composition."
        ),
    ):
        model_root(architecture, orphan)


# ---------------------------------------------------------------------------
# One binding per usage
# ---------------------------------------------------------------------------


def test_a_usage_redefining_two_features_is_rejected(tmp_path: Path) -> None:
    architecture = _load_text(
        tmp_path, fixture_text("selection/multi-redefine.sysml")
    )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "usage 'both' in configuration 'BadSystem' redefines more than one "
            "feature (source, gain); bind exactly one variation point."
        ),
    ):
        derived_selection(architecture, "bad")


# ---------------------------------------------------------------------------
# A binding value must name one variant of the point
# ---------------------------------------------------------------------------


def test_a_qualified_binding_must_name_the_points_definition(
    tmp_path: Path,
) -> None:
    architecture = _load_text(
        tmp_path, fixture_text("selection/binding-errors.sysml")
    )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "binding 'OtherChoice::thing' for variation point 'SourceChoice' at "
            "'source' names type 'OtherChoice'; expected 'SourceChoice'"
        ),
    ):
        derived_selection(architecture, "wrong_type")


def test_an_unqualified_binding_must_name_a_local_usage(tmp_path: Path) -> None:
    architecture = _load_text(
        tmp_path, fixture_text("selection/binding-errors.sysml")
    )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "binding 'missingUsage' for variation point 'SourceChoice' at "
            "'source' names no part usage in configuration 'NoLocalSystem'"
        ),
    ):
        derived_selection(architecture, "no_local")


def test_a_local_usage_must_specialise_one_variant(tmp_path: Path) -> None:
    architecture = _load_text(
        tmp_path, fixture_text("selection/binding-errors.sysml")
    )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "part usage 'local' in configuration 'NoSubsetSystem' must specialise "
            "exactly one variant of 'SourceChoice'; found 0"
        ),
    ):
        derived_selection(architecture, "no_subset")


def test_a_local_usage_specialising_two_variants_is_rejected(
    tmp_path: Path,
) -> None:
    architecture = _load_text(
        tmp_path, fixture_text("selection/binding-errors.sysml")
    )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "part usage 'local' in configuration 'TwoSubsetSystem' must "
            "specialise exactly one variant of 'SourceChoice'; found 2"
        ),
    ):
        derived_selection(architecture, "two_subsets")


def test_a_local_usage_must_specialise_a_variant_of_the_point(
    tmp_path: Path,
) -> None:
    architecture = _load_text(
        tmp_path, fixture_text("selection/binding-errors.sysml")
    )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "part usage 'local' in configuration 'NotVariantSystem' specialises "
            "'OtherChoice::thing', which is not a variant of 'SourceChoice'"
        ),
    ):
        derived_selection(architecture, "not_variant")


# ---------------------------------------------------------------------------
# Unknown variants and rebinding
# ---------------------------------------------------------------------------


def test_an_unknown_variant_is_rejected_in_a_nested_scope(
    tmp_path: Path,
) -> None:
    architecture = _load_text(
        tmp_path, fixture_text("selection/nested-unknown-variant.sysml")
    )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Unknown variant 'missing' for variation point 'BChoice' at "
            "'top.inner' in configuration 'Config'; expected one of b1."
        ),
    ):
        derived_selection(architecture, "conf")


def test_a_more_derived_configuration_overrides_an_inherited_binding(
    tmp_path: Path,
) -> None:
    architecture = _load_text(tmp_path, fixture_text("selection/rebinding.sysml"))

    assert derived_selection(architecture, "direct") == {"path": "directPath"}


# ---------------------------------------------------------------------------
# Attribute points bound by a configuration
# ---------------------------------------------------------------------------


def test_a_configuration_binds_an_attribute_point_structurally(
    tmp_path: Path,
) -> None:
    path = tmp_path / "attribute-binding.sysml"
    write_model(path, fixture_text("selection/attribute-binding.sysml"))
    architecture = load(path)

    assert derived_selection(architecture, "configured") == {
        "scenario": "nominalK3"
    }
    plan = next(
        plan for plan in analysis_plans(architecture) if plan.name == "configured"
    )
    assert plan.status == "legal"
    assert plan.configuration == "Configured"
    assert plan.selection == {"scenario": "nominalK3"}

    artifacts = generate_analysis(
        path,
        tmp_path / "analysis",
        "configured",
        model_name="attribute-binding",
    )
    descriptor = json.loads(artifacts.descriptor.read_text(encoding="utf-8"))
    assert descriptor["composition"] == "Root"


def test_an_attribute_configuration_rejects_an_unknown_variant(
    tmp_path: Path,
) -> None:
    architecture = _load_text(
        tmp_path, fixture_text("selection/attribute-binding.sysml")
    )

    with pytest.raises(
        ValueError,
        match=(
            "Unknown variant 'missing' for variation point 'ScenarioChoice' at "
            "'scenario' in configuration 'BadConfigured'"
        ),
    ):
        derived_selection(architecture, "bad")


def test_a_model_attribute_binding_resolves_on_the_root(tmp_path: Path) -> None:
    architecture = _load_text(
        tmp_path, fixture_text("selection/attribute-binding.sysml")
    )

    resolved, canonical = resolve_selected(
        architecture, "Root", {"scenario": "nominalK3"}
    )

    assert canonical == {"scenario": "nominalK3"}
    assert (
        resolved.part_definitions["Root"].attributes["scenario"].type_name
        == "ScenarioK3"
    )


def test_attribute_ambiguity_still_fires_for_distinct_usages(
    tmp_path: Path,
) -> None:
    architecture = _load_text(
        tmp_path, fixture_text("selection/attribute-ambiguous.sysml")
    )

    with pytest.raises(
        ValueError,
        match="Selection key 'mode' is ambiguous.*'mode', 'inner.x.mode'",
    ):
        resolve_selected(architecture, "System", {"mode": "anything"})


# ---------------------------------------------------------------------------
# Per-analysis maps and plan classification
# ---------------------------------------------------------------------------


def test_analysis_selections_keeps_declaration_order(tmp_path: Path) -> None:
    architecture = _load_text(
        tmp_path, fixture_text("selection/analysis-order.sysml")
    )

    selections = analysis_selections(architecture)

    assert list(selections) == ["one", "second", "plain"]
    assert selections == {
        "one": {"source": "step"},
        "second": {"source": "sine"},
        "plain": {},
    }


def test_an_analysis_plan_rejects_an_unknown_status() -> None:
    with pytest.raises(
        ValueError,
        match=re.escape(
            "Unknown analysis plan status 'bogus'; expected one of legal, "
            "violated, invalid"
        ),
    ):
        AnalysisPlan("analysis", {}, "bogus")


def test_a_plan_marks_a_resolution_failure_invalid_and_keeps_the_selection(
    tmp_path: Path,
) -> None:
    architecture = _load_text(
        tmp_path, fixture_text("selection/unresolvable-variant.sysml")
    )
    plan = next(plan for plan in analysis_plans(architecture) if plan.name == "bad")

    assert plan.status == "invalid"
    assert plan.selection == {"source": "step"}
    assert plan.canonical is None
    assert (
        "Selected variant 'step' of variation point 'SourceChoice' has type "
        "'MissingType', which is not a part definition"
    ) in (plan.detail or "")
