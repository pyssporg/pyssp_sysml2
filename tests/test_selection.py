"""Configuration derivation, CLI selection parsing, and per-analysis plans."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyssp_sysml2.artifacts.analysis import generate_analysis
from pyssp_sysml2.model import Architecture, load
from pyssp_sysml2.parameters.configuration import (
    configuration_name,
    derived_selection,
    model_root,
)
from pyssp_sysml2.parameters.selection import (
    analysis_plans,
    analysis_selection,
    parse_selection,
)
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


def test_generate_analysis_defaults_to_the_derived_selection(
    tmp_path: Path,
) -> None:
    path, _ = _load(tmp_path)

    artifacts = generate_analysis(
        path,
        tmp_path / "analysis",
        "nested_gain",
        model_name="selection",
    )

    assert artifacts.descriptor.is_file()


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
