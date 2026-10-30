"""Evaluate captured SysML constraints after variation selection.

The adapter records ``constraint def`` bodies and ``constraint`` usages (see
:mod:`pyssp_sysml2.model`). This module evaluates the small boolean subset the
simulation dialect uses, against the variant selection that was just resolved:

- ``==``, ``!=``;
- ``implies`` (right-associative);
- ``and``, ``or``, ``xor``, ``not``;
- parentheses;
- references, where ``Type::member`` evaluates to ``member`` and a bare
  reference uses its bound selection value.

Evaluation happens after :func:`pyssp_sysml2.parameters.variation.resolve`, so
an illegal ``--select`` is rejected before any artifact is written.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pyssp_sysml2.model import (
    Architecture,
    ConstraintDefinition,
    ConstraintUsage,
    PartDefinition,
)

__all__ = [
    "ConstraintReport",
    "ConstraintResult",
    "ConstraintViolation",
    "enforce_constraints",
    "evaluate",
]

_STATUSES = ("pass", "fail", "invalid", "unasserted")


@dataclass(frozen=True)
class ConstraintResult:
    """One constraint usage's outcome.

    ``status`` is ``"pass"``, ``"fail"``, ``"invalid"``, or ``"unasserted"``.
    ``owner`` is the dotted part-usage path owning the usage (``""`` at the
    composition root).
    """

    name: str
    owner: str
    status: str
    detail: str | None = None


@dataclass(frozen=True)
class ConstraintReport:
    """Every constraint result reachable from one composition."""

    results: tuple[ConstraintResult, ...]

    def _with_status(self, status: str) -> tuple[ConstraintResult, ...]:
        return tuple(result for result in self.results if result.status == status)

    @property
    def passed(self) -> tuple[ConstraintResult, ...]:
        return self._with_status("pass")

    @property
    def failed(self) -> tuple[ConstraintResult, ...]:
        return self._with_status("fail")

    @property
    def invalid(self) -> tuple[ConstraintResult, ...]:
        return self._with_status("invalid")

    @property
    def unasserted(self) -> tuple[ConstraintResult, ...]:
        return self._with_status("unasserted")

    @property
    def ok(self) -> bool:
        """Whether every asserted constraint passed or was not evaluated."""
        return not self.failed and not self.invalid

    @property
    def detail(self) -> str | None:
        """One-line summary of every blocking result, or ``None`` when clear."""
        blocking = self.failed + self.invalid
        if not blocking:
            return None
        details = []
        for result in blocking:
            where = result.owner or "<root>"
            detail = f" ({result.detail})" if result.detail else ""
            details.append(f"{where}: {result.name} {result.status}{detail}")
        return "; ".join(details)

    def enforce(self) -> None:
        """Raise :class:`ConstraintViolation` on any asserted fail or invalid."""
        detail = self.detail
        if detail is None:
            return
        raise ConstraintViolation("constraint check failed: " + detail)


class ConstraintViolation(ValueError):
    """An asserted constraint failed or could not be evaluated."""


# -- reachability -----------------------------------------------------------


def _join(owner: str, name: str) -> str:
    return f"{owner}.{name}" if owner else name


def _walk(
    architecture: Architecture,
    definition: PartDefinition,
    owner: str,
    selections: Mapping[str, str],
    results: list[ConstraintResult],
    stack: frozenset[str],
) -> None:
    for usage in definition.constraints:
        results.append(_evaluate_usage(architecture, usage, owner, selections))
    for part_usage in definition.parts.values():
        child = architecture.resolve_part(part_usage)
        if child is None or child.name in stack:
            continue
        _walk(
            architecture,
            child,
            _join(owner, part_usage.name),
            selections,
            results,
            stack | {child.name},
        )


def evaluate(
    architecture: Architecture,
    composition: PartDefinition | str,
    selections: Mapping[str, str] | None = None,
) -> ConstraintReport:
    """Evaluate every constraint reachable from *composition*.

    Non-asserted usages are reported as ``"unasserted"``. An asserted usage
    whose binding is missing from *selections* is ``"invalid"``; this function
    always reports that, while :func:`enforce_constraints` chooses not to raise
    when no selection was requested at all.
    """
    definition = (
        composition
        if isinstance(composition, PartDefinition)
        else architecture.get_part_def(composition)
    )
    results: list[ConstraintResult] = []
    _walk(
        architecture,
        definition,
        "",
        dict(selections or {}),
        results,
        frozenset({definition.name}),
    )
    return ConstraintReport(tuple(results))


def enforce_constraints(
    architecture: Architecture,
    composition: PartDefinition | str,
    selections: Mapping[str, str] | None = None,
) -> None:
    """Raise when the requested selection violates an asserted constraint.

    An empty or ``None`` *selections* means no variant selection was requested:
    there is no selection legality to check, so this returns without raising.
    Callers that only want a report should use :func:`evaluate`.
    """
    if not selections:
        return
    evaluate(architecture, composition, selections).enforce()


# -- one usage --------------------------------------------------------------


def _evaluate_usage(
    architecture: Architecture,
    usage: ConstraintUsage,
    owner: str,
    selections: Mapping[str, str],
) -> ConstraintResult:
    name = usage.name or "<anonymous>"
    if not usage.asserted:
        return ConstraintResult(name=name, owner=owner, status="unasserted")
    try:
        expression, definition = _expression_for(architecture, usage)
        bindings = _bind(usage, owner, selections)
        _check_parameters(definition, bindings)
        value = _Expression(bindings).evaluate(expression)
        if not isinstance(value, bool):
            raise _Invalid(
                f"expression '{expression}' is not boolean but {type(value).__name__}"
            )
        if usage.negated:
            value = not value
        if value:
            return ConstraintResult(name=name, owner=owner, status="pass")
        return ConstraintResult(
            name=name,
            owner=owner,
            status="fail",
            detail=f"'{expression}' is false",
        )
    except _Invalid as error:
        return ConstraintResult(
            name=name, owner=owner, status="invalid", detail=str(error)
        )


def _expression_for(
    architecture: Architecture, usage: ConstraintUsage
) -> tuple[str, ConstraintDefinition | None]:
    definition = None
    if usage.type_name:
        definition = architecture.constraint_definitions.get(usage.type_name)
        if definition is None:
            raise _Invalid(f"unknown constraint definition '{usage.type_name}'")
    expression = usage.expression or (definition.expression if definition else None)
    if not expression:
        raise _Invalid("constraint has no expression")
    return expression, definition


def _bind(
    usage: ConstraintUsage,
    owner: str,
    selections: Mapping[str, str],
) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for parameter, reference in usage.bindings.items():
        absolute = _join(owner, reference)
        if absolute not in selections:
            raise _Invalid(
                f"no selection for '{absolute}' bound to '{parameter}'"
            )
        bindings[parameter] = selections[absolute]
    return bindings


def _check_parameters(
    definition: ConstraintDefinition | None, bindings: dict[str, str]
) -> None:
    if definition is None:
        return
    missing = sorted(set(definition.parameters) - set(bindings))
    if missing:
        raise _Invalid("unbound parameter(s): " + ", ".join(missing))


# -- expression subset ------------------------------------------------------


class _Invalid(Exception):
    """A malformed or unresolvable constraint expression."""


_OPERATORS = {"implies", "and", "or", "xor", "not"}


def _tokenize(text: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char.isspace():
            index += 1
            continue
        if text.startswith("==", index) or text.startswith("!=", index):
            tokens.append(("op", text[index : index + 2]))
            index += 2
            continue
        if char in "()":
            tokens.append(("op", char))
            index += 1
            continue
        if char == '"':
            end = index + 1
            escaped = False
            chars: list[str] = []
            while end < length:
                current = text[end]
                if escaped:
                    chars.append(current)
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    end += 1
                    break
                else:
                    chars.append(current)
                end += 1
            else:
                raise _Invalid("unterminated string literal")
            tokens.append(("string", "".join(chars)))
            index = end
            continue
        if char.isalpha() or char == "_":
            end = index
            while end < length:
                if text[end].isalnum() or text[end] == "_":
                    end += 1
                elif text.startswith("::", end):
                    end += 2
                else:
                    break
            tokens.append(("word", text[index:end]))
            index = end
            continue
        raise _Invalid(f"unexpected character '{char}' in expression")
    return tokens


class _Expression:
    """Recursive-descent evaluator for the documented boolean subset."""

    def __init__(self, bindings: Mapping[str, str]) -> None:
        self._bindings = bindings
        self._tokens: list[tuple[str, str]] = []
        self._position = 0

    def evaluate(self, text: str):
        self._tokens = _tokenize(text)
        self._position = 0
        if not self._tokens:
            raise _Invalid("empty constraint expression")
        value = self._implies()
        if self._position != len(self._tokens):
            raise _Invalid(f"unexpected token '{self._peek()[1]}'")
        return value

    # -- token helpers ------------------------------------------------------

    def _peek(self) -> tuple[str, str]:
        if self._position >= len(self._tokens):
            return ("eof", "")
        return self._tokens[self._position]

    def _take(self) -> tuple[str, str]:
        token = self._peek()
        self._position += 1
        return token

    def _accept_word(self, word: str) -> bool:
        kind, value = self._peek()
        if kind == "word" and value == word:
            self._position += 1
            return True
        return False

    def _accept_op(self, operator: str) -> bool:
        kind, value = self._peek()
        if kind == "op" and value == operator:
            self._position += 1
            return True
        return False

    # -- precedence ---------------------------------------------------------

    def _implies(self):
        left = self._or()
        if self._accept_word("implies"):
            right = self._implies()
            return (not _as_bool(left, "implies")) or _as_bool(right, "implies")
        return left

    def _or(self):
        left = self._xor()
        while self._accept_word("or"):
            left = _as_bool(left, "or") or _as_bool(self._xor(), "or")
        return left

    def _xor(self):
        left = self._and()
        while self._accept_word("xor"):
            left = _as_bool(left, "xor") != _as_bool(self._and(), "xor")
        return left

    def _and(self):
        left = self._equality()
        while self._accept_word("and"):
            left = _as_bool(left, "and") and _as_bool(self._equality(), "and")
        return left

    def _equality(self):
        left = self._unary()
        while True:
            kind, value = self._peek()
            if kind != "op" or value not in ("==", "!="):
                return left
            self._position += 1
            right = self._unary()
            left = (left == right) if value == "==" else (left != right)

    def _unary(self):
        if self._accept_word("not"):
            return not _as_bool(self._unary(), "not")
        return self._primary()

    def _primary(self):
        kind, value = self._peek()
        if kind == "op" and value == "(":
            self._position += 1
            inner = self._implies()
            if not self._accept_op(")"):
                raise _Invalid("missing ')' in expression")
            return inner
        if kind == "string":
            self._position += 1
            return value
        if kind == "word":
            self._position += 1
            if value == "true":
                return True
            if value == "false":
                return False
            if "::" in value:
                return value.rsplit("::", 1)[-1]
            if value in self._bindings:
                return self._bindings[value]
            raise _Invalid(f"unbound reference '{value}'")
        raise _Invalid("unexpected end of expression")


def _as_bool(value, operator: str) -> bool:
    if not isinstance(value, bool):
        raise _Invalid(
            f"'{operator}' needs boolean operands, got {type(value).__name__}"
        )
    return value
