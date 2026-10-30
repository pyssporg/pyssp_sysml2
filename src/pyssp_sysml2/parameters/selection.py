"""Authored variation selections and per-analysis legality plans.

An analysis declares the variants it composes with one control attribute::

    part def step_two :> Analysis {
      attribute pyssp_selection = "source=stepImplementation;gain=twoStages";
      ...
    }

The value uses the same language as the CLI ``--select`` flag. A plan resolves
the selection, evaluates the constraints reachable from the analysis, and
classifies the analysis as:

- ``legal``: the selection resolves and every asserted constraint passes;
- ``violated``: the selection resolves but an asserted constraint fails;
- ``invalid``: the selection is missing, malformed, or does not resolve, or a
  constraint could not be evaluated.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pyssp_sysml2.core.control import SELECTION_ATTR
from pyssp_sysml2.metadata.roles import analysis_part_definitions
from pyssp_sysml2.model import Architecture, PartDefinition
from pyssp_sysml2.parameters.constraints import ConstraintReport, evaluate
from pyssp_sysml2.parameters.variation import resolve_selected

__all__ = [
    "AnalysisPlan",
    "analysis_plans",
    "analysis_selection",
    "analysis_selections",
    "parse_selection",
]

_STATUSES = ("legal", "violated", "invalid")


@dataclass(frozen=True)
class AnalysisPlan:
    """One analysis and the outcome of its authored selection.

    ``selection`` keeps the authored key language so it can be handed to a
    build unchanged. ``canonical`` is the resolved key map used for constraint
    evaluation; it is empty when the selection could not be resolved.
    """

    name: str
    selection: Mapping[str, str]
    status: str
    detail: str | None = None
    canonical: Mapping[str, str] | None = None
    report: ConstraintReport | None = None

    def __post_init__(self) -> None:
        if self.status not in _STATUSES:
            raise ValueError(
                f"Unknown analysis plan status '{self.status}'; expected one of "
                + ", ".join(_STATUSES)
            )

    @property
    def legal(self) -> bool:
        return self.status == "legal"


def parse_selection(text: str) -> dict[str, str]:
    """Parse ``key=variant;key=variant`` into a selection map.

    Whitespace around entries and around ``=`` is ignored. An empty entry is
    skipped, but an entry without ``=``, an empty key or variant, or a repeated
    key raises ``ValueError``.
    """
    selection: dict[str, str] = {}
    for part in text.split(";"):
        entry = part.strip()
        if not entry:
            continue
        if "=" not in entry:
            raise ValueError(
                f"invalid {SELECTION_ATTR} entry '{entry}'; expected "
                "'key=variant'"
            )
        key, variant = entry.split("=", 1)
        key = key.strip()
        variant = variant.strip()
        if not key or not variant:
            raise ValueError(
                f"invalid {SELECTION_ATTR} entry '{entry}'; key and variant "
                "must both be non-empty"
            )
        if key in selection:
            raise ValueError(
                f"{SELECTION_ATTR} names variation point '{key}' twice"
            )
        selection[key] = variant
    return selection


def analysis_selection(
    architecture: Architecture, analysis: PartDefinition | str
) -> dict[str, str]:
    """The selection an analysis declares, or an empty map when none is given."""
    definition = (
        analysis
        if isinstance(analysis, PartDefinition)
        else architecture.get_part_def(analysis)
    )
    attribute = definition.attributes.get(SELECTION_ATTR)
    if attribute is None:
        return {}
    if attribute.value is None:
        raise ValueError(
            f"{definition.name}.{SELECTION_ATTR} must carry a value, for "
            "example \"source=stepImplementation\""
        )
    return parse_selection(str(attribute.value))


def analysis_selections(architecture: Architecture) -> dict[str, dict[str, str]]:
    """Every analysis's authored selection, in declaration order."""
    return {
        definition.name: analysis_selection(architecture, definition)
        for definition in analysis_part_definitions(architecture)
    }


def analysis_plans(architecture: Architecture) -> tuple[AnalysisPlan, ...]:
    """Classify every analysis by its authored selection.

    A selection that does not resolve is ``invalid``: that includes an analysis
    composing a varying model without declaring a selection. This is the
    adapter's verdict; a fixture still pins the set it expects.
    """
    plans: list[AnalysisPlan] = []
    for analysis in analysis_part_definitions(architecture):
        try:
            authored = analysis_selection(architecture, analysis)
        except ValueError as error:
            plans.append(
                AnalysisPlan(analysis.name, {}, "invalid", str(error))
            )
            continue
        try:
            resolved, canonical = resolve_selected(
                architecture, analysis, authored
            )
        except ValueError as error:
            plans.append(
                AnalysisPlan(analysis.name, authored, "invalid", str(error))
            )
            continue

        report = evaluate(resolved, analysis.name, canonical)
        if report.invalid:
            status = "invalid"
        elif report.failed:
            status = "violated"
        else:
            status = "legal"
        plans.append(
            AnalysisPlan(
                name=analysis.name,
                selection=authored,
                status=status,
                detail=report.detail,
                canonical=canonical,
                report=report,
            )
        )
    return tuple(plans)
