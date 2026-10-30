"""Authored selection parsing and per-analysis legality plans."""

from __future__ import annotations

import pytest

from pyssp_sysml2.artifacts.analysis import generate_analysis
from pyssp_sysml2.model import load
from pyssp_sysml2.parameters.selection import (
    analysis_plans,
    analysis_selection,
    parse_selection,
)
from tests.fixture_files import fixture_text
from tests.testhelpers import write_model


def _load(tmp_path):
    path = tmp_path / "selection.sysml"
    write_model(path, fixture_text("selection/selection.sysml"))
    return path, load(path)


def _plans(tmp_path):
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


def test_analysis_selection_reads_the_control_attribute(tmp_path) -> None:
    _, architecture = _load(tmp_path)

    assert analysis_selection(architecture, "step_single") == {
        "source": "stepImplementation",
        "gain": "singleStage",
    }
    assert analysis_selection(architecture, "missing") == {}


def test_plans_classify_legal_violated_and_invalid(tmp_path) -> None:
    plans = _plans(tmp_path)

    assert plans["step_single"].status == "legal"
    assert plans["step_single"].legal is True
    assert plans["step_single"].canonical == {
        "sut.source": "stepImplementation",
        "sut.gain": "singleStage",
    }

    assert plans["sine_two"].status == "violated"
    assert "requiresSingleStage fail" in (plans["sine_two"].detail or "")

    assert plans["broken"].status == "invalid"
    assert "expected 'key=variant'" in (plans["broken"].detail or "")

    assert plans["missing"].status == "invalid"
    assert "is not selected" in (plans["missing"].detail or "")


def test_generate_analysis_defaults_to_the_authored_selection(tmp_path) -> None:
    path, _ = _load(tmp_path)

    artifacts = generate_analysis(
        path,
        tmp_path / "analysis",
        "step_single",
        model_name="selection",
    )

    assert artifacts.descriptor.is_file()


def test_an_explicit_selection_overrides_the_authored_one(tmp_path) -> None:
    path, _ = _load(tmp_path)

    with pytest.raises(ValueError, match="constraint check failed"):
        generate_analysis(
            path,
            tmp_path / "analysis",
            "step_single",
            model_name="selection",
            selections={"source": "sineImplementation", "gain": "twoStage"},
        )
