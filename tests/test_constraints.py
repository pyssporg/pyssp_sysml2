"""Constraint capture and evaluation on the repo-owned model.

The fixture carries one package-level ``constraint def`` with two usage bindings
and one asserted usage. Evaluation runs after variation selection, so an
illegal selection fails before generation.
"""

from __future__ import annotations

import pytest

from pyssp_sysml2.model import (
    Architecture,
    ConstraintUsage,
    PartDefinition,
    load,
)
from pyssp_sysml2.parameters.constraints import (
    ConstraintReport,
    ConstraintResult,
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


# ---------------------------------------------------------------------------
# Helpers for the focused fixtures below
# ---------------------------------------------------------------------------


def _load_fixture(tmp_path, name: str) -> Architecture:
    path = tmp_path / name
    write_model(path, fixture_text(f"constraints/{name}"))
    return load(path)


def _only_result(report: ConstraintReport):
    assert len(report.results) == 1
    return report.results[0]


def _inline_architecture(expression: str) -> Architecture:
    """Smallest public model: one asserted usage carrying one expression.

    Tokenizer and parser errors cannot be written into a SysML fixture (the
    adapter parser rejects them first), so they are reached here through the
    public dataclasses and :func:`evaluate`.
    """
    usage = ConstraintUsage(name="inlineCheck", expression=expression, asserted=True)
    part_def = PartDefinition(name="InlineComposition", constraints=[usage])
    return Architecture(
        package_name="Inline", part_definitions={"InlineComposition": part_def}
    )


def _inline_detail(expression: str) -> str | None:
    report = evaluate(_inline_architecture(expression), "InlineComposition", {})
    result = _only_result(report)
    assert result.status == "invalid"
    return result.detail


# ---------------------------------------------------------------------------
# Negated assert
# ---------------------------------------------------------------------------

NEGATED = "NegatedComposition"


def test_negated_assert_is_captured(tmp_path) -> None:
    architecture = _load_fixture(tmp_path, "negated.sysml")

    usage = architecture.get_part_def(NEGATED).constraints[0]
    assert usage.name == "mustBeOff"
    assert usage.asserted is True
    assert usage.negated is True
    assert usage.bindings == {"chosen": "selected"}


def test_negated_assert_passes_when_expression_is_false(tmp_path) -> None:
    architecture = _load_fixture(tmp_path, "negated.sysml")

    report = evaluate(architecture, NEGATED, {"selected": "off"})

    assert [result.name for result in report.passed] == ["mustBeOff"]
    assert report.failed == ()
    assert report.ok is True
    assert report.detail is None


def test_negated_assert_fails_when_expression_is_true(tmp_path) -> None:
    architecture = _load_fixture(tmp_path, "negated.sysml")

    report = evaluate(architecture, NEGATED, {"selected": "on"})

    assert [result.name for result in report.failed] == ["mustBeOff"]
    assert report.ok is False
    assert report.failed[0].detail == "'chosen == ModeChoice::on' is true"
    assert report.detail == (
        "<root>: mustBeOff fail ('chosen == ModeChoice::on' is true)"
    )


# ---------------------------------------------------------------------------
# Nested / deep scope propagation
# ---------------------------------------------------------------------------

NESTED = "NestedComposition"
NESTED_KEY = "sut.inner.selected"
NESTED_EXPRESSION = "chosen == ModeChoice::on"


def test_nested_scope_evaluates_at_composed_path(tmp_path) -> None:
    architecture = _load_fixture(tmp_path, "nested-scope.sysml")

    result = _only_result(evaluate(architecture, NESTED, {NESTED_KEY: "on"}))

    assert (result.name, result.owner, result.status) == (
        "innerAssertion",
        "sut.inner",
        "pass",
    )


def test_nested_scope_failure_names_owner_path(tmp_path) -> None:
    architecture = _load_fixture(tmp_path, "nested-scope.sysml")

    report = evaluate(architecture, NESTED, {NESTED_KEY: "off"})

    assert report.detail == (
        f"sut.inner: innerAssertion fail ('{NESTED_EXPRESSION}' is false)"
    )


def test_nested_scope_missing_selection_uses_composed_key(tmp_path) -> None:
    architecture = _load_fixture(tmp_path, "nested-scope.sysml")

    result = _only_result(evaluate(architecture, NESTED, {}))

    assert result.status == "invalid"
    assert result.detail == f"no selection for '{NESTED_KEY}' bound to 'chosen'"


# ---------------------------------------------------------------------------
# Effective members: inheritance and override
# ---------------------------------------------------------------------------

OVERRIDDEN = "OverriddenComposition"


def test_derived_constraint_replaces_inherited_usage_by_name(tmp_path) -> None:
    architecture = _load_fixture(tmp_path, "overridden.sysml")

    report = evaluate(architecture, OVERRIDDEN, {})

    # One entry, at the inherited position, now carrying the derived type.
    assert [result.name for result in report.results] == [
        "inheritedRule",
        "<anonymous>",
        "ownRule",
    ]
    assert [(result.name, result.status) for result in report.results] == [
        ("inheritedRule", "fail"),
        ("<anonymous>", "unasserted"),
        ("ownRule", "pass"),
    ]
    assert report.detail == "rules: inheritedRule fail ('false' is false)"


def test_unnamed_inherited_constraint_is_never_overridden(tmp_path) -> None:
    architecture = _load_fixture(tmp_path, "overridden.sysml")

    report = evaluate(architecture, OVERRIDDEN, {})

    anonymous = [result for result in report.results if result.name == "<anonymous>"]
    assert len(anonymous) == 1
    assert (anonymous[0].owner, anonymous[0].status) == ("rules", "unasserted")


# ---------------------------------------------------------------------------
# Expression language
# ---------------------------------------------------------------------------

EXPRESSIONS = "ExpressionsComposition"
EXPRESSION_SELECTIONS = {"selected": "off"}


def _expression_result(tmp_path, name: str):
    architecture = _load_fixture(tmp_path, "expressions.sysml")
    report = evaluate(architecture, EXPRESSIONS, EXPRESSION_SELECTIONS)
    return {result.name: result for result in report.results}[name]


def test_implies_is_right_associative(tmp_path) -> None:
    result = _expression_result(tmp_path, "impliesAssociates")

    assert (result.status, result.detail) == ("pass", None)


def test_implies_is_vacuously_true(tmp_path) -> None:
    result = _expression_result(tmp_path, "impliesVacuous")

    assert (result.status, result.detail) == ("pass", None)


def test_parentheses_override_associativity(tmp_path) -> None:
    result = _expression_result(tmp_path, "parentheses")

    assert result.status == "fail"
    assert result.detail == "'(false implies false) implies false' is false"


def test_string_literal_escape(tmp_path) -> None:
    result = _expression_result(tmp_path, "escapedString")

    assert (result.status, result.detail) == ("pass", None)


def test_type_member_evaluates_to_member_and_bypasses_bindings(tmp_path) -> None:
    architecture = _load_fixture(tmp_path, "expressions.sysml")
    usage = {
        item.name: item
        for item in architecture.get_part_def(EXPRESSIONS).constraints
    }["typeMember"]
    assert usage.bindings == {"Choice": "selected"}

    # The binding resolves to "off"; ``Choice::on`` must not consult it.
    result = _expression_result(tmp_path, "typeMember")

    assert (result.status, result.detail) == ("pass", None)


def test_boolean_literals(tmp_path) -> None:
    assert _expression_result(tmp_path, "trueLiteral").status == "pass"

    false_result = _expression_result(tmp_path, "falseLiteral")
    assert false_result.status == "fail"
    assert false_result.detail == "'false' is false"


def test_non_boolean_operand_is_invalid(tmp_path) -> None:
    result = _expression_result(tmp_path, "nonBooleanOperand")

    assert result.status == "invalid"
    assert result.detail == "'and' needs boolean operands, got str"


def test_non_boolean_value_is_invalid(tmp_path) -> None:
    result = _expression_result(tmp_path, "nonBooleanValue")

    assert result.status == "invalid"
    assert result.detail == "expression 'Choice::on' is not boolean but str"


def test_not_binds_tighter_than_equality(tmp_path) -> None:
    result = _expression_result(tmp_path, "notBindsTighterThanEquality")

    assert result.status == "invalid"
    assert result.detail == "'not' needs boolean operands, got str"


def test_and_binds_tighter_than_or(tmp_path) -> None:
    # false and (true or true) is false; (false and true) or true is true.
    result = _expression_result(tmp_path, "andOverOr")

    assert (result.status, result.detail) == ("pass", None)


def test_or_binds_tighter_than_xor(tmp_path) -> None:
    # (true xor false) or true is true; true xor (false or true) is false.
    result = _expression_result(tmp_path, "orOverXor")

    assert (result.status, result.detail) == ("pass", None)


def test_xor_binds_tighter_than_and(tmp_path) -> None:
    # true xor (false and false) is true; (true xor false) and false is false.
    result = _expression_result(tmp_path, "xorOverAnd")

    assert (result.status, result.detail) == ("pass", None)


def test_non_boolean_right_operand_is_invalid(tmp_path) -> None:
    expected = {
        "nonBooleanRightOr": "'or' needs boolean operands, got str",
        "nonBooleanRightAnd": "'and' needs boolean operands, got str",
        "nonBooleanRightXor": "'xor' needs boolean operands, got str",
        "nonBooleanRightImplies": "'implies' needs boolean operands, got str",
    }
    for name, detail in expected.items():
        result = _expression_result(tmp_path, name)
        assert (result.status, result.detail) == ("invalid", detail), name


# ---------------------------------------------------------------------------
# Resolution errors: definition, expression, parameters, selection
# ---------------------------------------------------------------------------

RESOLUTION = "ResolutionComposition"


def _resolution_results(tmp_path) -> dict[str, ConstraintResult]:
    architecture = _load_fixture(tmp_path, "resolution.sysml")
    report = evaluate(architecture, RESOLUTION, {"selected": "on"})
    return {result.name: result for result in report.results}


def test_unknown_constraint_definition(tmp_path) -> None:
    result = _resolution_results(tmp_path)["ghost"]

    assert result.status == "invalid"
    assert result.detail == "unknown constraint definition 'MissingConstraint'"


def test_constraint_without_expression(tmp_path) -> None:
    result = _resolution_results(tmp_path)["bare"]

    assert result.status == "invalid"
    assert result.detail == "constraint has no expression"


def test_unbound_parameter(tmp_path) -> None:
    result = _resolution_results(tmp_path)["missingBinding"]

    assert result.status == "invalid"
    assert result.detail == "unbound parameter(s): beta"


def test_missing_selection_names_absolute_key(tmp_path) -> None:
    architecture = _load_constraints(tmp_path)

    report = evaluate(architecture, COMPOSITION, {"source": "sineImplementation"})

    result = {
        item.name: item for item in report.results if item.name == "requiresSingleStage"
    }["requiresSingleStage"]
    assert result.status == "invalid"
    assert result.detail == "no selection for 'gain' bound to 'chosenGain'"


# ---------------------------------------------------------------------------
# Tokenizer and parser errors (in-memory architecture; see helper)
# ---------------------------------------------------------------------------


def test_unexpected_character_is_invalid() -> None:
    assert _inline_detail("true & false") == (
        "unexpected character '&' in expression"
    )


def test_unterminated_string_is_invalid() -> None:
    assert _inline_detail('"abc') == "unterminated string literal"


def test_empty_expression_is_invalid() -> None:
    assert _inline_detail("   ") == "empty constraint expression"


def test_unexpected_token_is_invalid() -> None:
    assert _inline_detail("true false") == "unexpected token 'false'"


def test_missing_closing_parenthesis_is_invalid() -> None:
    assert _inline_detail("(true") == "missing ')' in expression"


def test_unexpected_end_of_expression_is_invalid() -> None:
    assert _inline_detail("true and") == "unexpected end of expression"


# ---------------------------------------------------------------------------
# enforce_constraints with no requested selection
# ---------------------------------------------------------------------------


def test_enforce_skips_none_and_empty_selection(tmp_path) -> None:
    architecture = _load_fixture(tmp_path, "expressions.sysml")

    assert enforce_constraints(architecture, EXPRESSIONS, None) is None
    assert enforce_constraints(architecture, EXPRESSIONS, {}) is None

    report = evaluate(architecture, EXPRESSIONS, None)
    assert [result.name for result in report.failed] == [
        "parentheses",
        "falseLiteral",
    ]
    assert report.ok is False
    with pytest.raises(ConstraintViolation):
        report.enforce()


# ---------------------------------------------------------------------------
# ConstraintReport surface
# ---------------------------------------------------------------------------


def test_report_filters_and_detail_format(tmp_path) -> None:
    architecture = _load_constraints(tmp_path)

    illegal = evaluate(architecture, COMPOSITION, ILLEGAL)

    assert illegal.ok is False
    assert illegal.passed == ()
    assert [result.name for result in illegal.failed] == ["requiresSingleStage"]
    assert illegal.invalid == ()
    assert [result.name for result in illegal.unasserted] == ["advisorySingleStage"]
    assert illegal.detail == (
        f"<root>: requiresSingleStage fail ('{EXPRESSION}' is false)"
    )

    legal = evaluate(architecture, COMPOSITION, LEGAL)

    assert legal.ok is True
    assert [result.name for result in legal.passed] == ["requiresSingleStage"]
    assert legal.detail is None
