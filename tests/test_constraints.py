"""Constraint capture and evaluation on the repo-owned model.

The fixture carries one package-level ``constraint def`` with two usage bindings
and one asserted usage. Evaluation runs after variation selection, so an
illegal selection fails before generation.
"""

from __future__ import annotations

import pytest

from pyssp_sysml2.model import load
from pyssp_sysml2.parameters.constraints import (
    ConstraintViolation,
    enforce_constraints,
    evaluate,
)
from tests.fixture_files import fixture_text
from tests.testhelpers import write_model


COMPOSITION = "ConstrainedComposition"
CONSTRAINT_DEF = "SineRequiresSingleStage"
EXPRESSION = (
    "chosenSource == SourceChoice::sineImplementation"
    " implies chosenGain == GainChoice::singleStage"
)
LEGAL = {"source": "sineImplementation", "gain": "singleStage"}
ILLEGAL = {"source": "sineImplementation", "gain": "twoStage"}


def _load_constraints(tmp_path):
    path = tmp_path / "constraints.sysml"
    write_model(path, fixture_text("constraints/constraints.sysml"))
    return load(path)


def test_capture_constraint_definition_and_usages(tmp_path) -> None:
    """The adapter records the definition body, usage bindings, and assert."""
    architecture = _load_constraints(tmp_path)

    definition = architecture.get_constraint_def(CONSTRAINT_DEF)
    assert definition.name == CONSTRAINT_DEF
    assert definition.parameters == {}
    assert definition.expression == EXPRESSION

    composition = architecture.get_part_def(COMPOSITION)
    by_name = {usage.name: usage for usage in composition.constraints}
    assert set(by_name) == {"requiresSingleStage", "advisorySingleStage"}

    asserted = by_name["requiresSingleStage"]
    assert asserted.type_name == CONSTRAINT_DEF
    assert asserted.bindings == {"chosenSource": "source", "chosenGain": "gain"}
    assert asserted.asserted is True
    assert asserted.negated is False

    advisory = by_name["advisorySingleStage"]
    assert advisory.bindings == {"chosenSource": "source", "chosenGain": "gain"}
    assert advisory.asserted is False


def test_legal_selection_passes(tmp_path) -> None:
    architecture = _load_constraints(tmp_path)

    report = evaluate(architecture, COMPOSITION, LEGAL)

    by_name = {result.name: result for result in report.results}
    assert by_name["requiresSingleStage"].status == "pass"
    assert by_name["advisorySingleStage"].status == "unasserted"
    assert report.failed == ()
    assert report.invalid == ()
    enforce_constraints(architecture, COMPOSITION, LEGAL)


def test_illegal_selection_fails_with_constraint_name(tmp_path) -> None:
    architecture = _load_constraints(tmp_path)

    report = evaluate(architecture, COMPOSITION, ILLEGAL)

    assert [result.name for result in report.failed] == ["requiresSingleStage"]
    with pytest.raises(ConstraintViolation) as excinfo:
        enforce_constraints(architecture, COMPOSITION, ILLEGAL)
    assert "requiresSingleStage" in str(excinfo.value)


def test_missing_selection_is_invalid(tmp_path) -> None:
    architecture = _load_constraints(tmp_path)

    report = evaluate(architecture, COMPOSITION, {"source": "sineImplementation"})

    invalid = [result for result in report.invalid if result.name == "requiresSingleStage"]
    assert len(invalid) == 1
    assert "'gain'" in (invalid[0].detail or "")


def test_unasserted_usage_is_reported_and_never_raises(tmp_path) -> None:
    architecture = _load_constraints(tmp_path)

    report = evaluate(architecture, COMPOSITION, ILLEGAL)

    unasserted = [result for result in report.unasserted]
    assert [result.name for result in unasserted] == ["advisorySingleStage"]


def test_no_constraint_architecture_reports_empty(tmp_path) -> None:
    """A model without constraints loads and enforces as a no-op."""
    path = tmp_path / "single.sysml"
    write_model(path, fixture_text("sysml-model/single.sysml"))
    architecture = load(path)

    report = evaluate(architecture, "Source", {})

    assert report.results == ()
    assert report.passed == ()
    assert report.failed == ()
    enforce_constraints(architecture, "Source", {})
