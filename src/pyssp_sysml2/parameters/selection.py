"""Derived variation selections and per-analysis legality plans.

An analysis composes a model-level SysML v2 configuration (see ``INFO-027``).
The configuration binds every variation point with a redefinition and a feature
value::

    part def StepSystem :> System {
      part :>> source = SourceChoice::step;
    }

:func:`pyssp_sysml2.parameters.configuration.derived_selection` turns that into
the canonical ``{"usage": "variant"}`` map. A plan resolves the map, evaluates
the constraints reachable from the analysis, and classifies the analysis as:

- ``legal``: the selection resolves and every asserted constraint passes;
- ``violated``: the selection resolves but an asserted constraint fails;
- ``invalid``: the configuration does not resolve, or a constraint could not be
  evaluated.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pyssp_sysml2.metadata.roles import analysis_part_definitions
from pyssp_sysml2.model import Architecture, PartDefinition
from pyssp_sysml2.parameters.configuration import (
    configuration_name,
    derived_selection,
)
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
    """One analysis and the outcome of its derived selection.

    ``configuration`` names the model configuration the analysis composes, or is
    ``None`` when it composes the root composition. ``selection`` keeps the
    derived key language so it can be handed to a build unchanged. ``canonical``
    is the resolved key map used for constraint evaluation; it is empty when the
    selection could not be resolved.
    """

    name: str
    selection: Mapping[str, str]
    status: str
    detail: str | None = None
    canonical: Mapping[str, str] | None = None
    report: ConstraintReport | None = None
    configuration: str | None = None

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

    This is the CLI ``--select`` language, not the authored model: whitespace
    around entries and around ``=`` is ignored. An empty entry is skipped, but an
    entry without ``=``, an empty key or variant, or a repeated key raises
    ``ValueError``.
    """
    selection: dict[str, str] = {}
    for part in text.split(";"):
        entry = part.strip()
        if not entry:
            continue
        if "=" not in entry:
            raise ValueError(
                f"invalid selection entry '{entry}'; expected 'key=variant'"
            )
        key, variant = entry.split("=", 1)
        key = key.strip()
        variant = variant.strip()
        if not key or not variant:
            raise ValueError(
                f"invalid selection entry '{entry}'; key and variant must both "
                "be non-empty"
            )
        if key in selection:
            raise ValueError(f"selection names variation point '{key}' twice")
        selection[key] = variant
    return selection


def analysis_selection(
    architecture: Architecture, analysis: PartDefinition | str
) -> dict[str, str]:
    """The selection the analysis's configuration derives."""
    return derived_selection(architecture, analysis)


def analysis_selections(architecture: Architecture) -> dict[str, dict[str, str]]:
    """Every analysis's derived selection, in declaration order."""
    return {
        definition.name: analysis_selection(architecture, definition)
        for definition in analysis_part_definitions(architecture)
    }


def analysis_plans(architecture: Architecture) -> tuple[AnalysisPlan, ...]:
    """Classify every analysis by its derived selection.

    A selection that does not resolve is ``invalid``: that includes a
    configuration that leaves a reachable variation point unbound. This is the
    adapter's verdict; a fixture still pins the set it expects.
    """
    plans: list[AnalysisPlan] = []
    for analysis in analysis_part_definitions(architecture):
        configuration: str | None = None
        try:
            configuration = configuration_name(architecture, analysis)
            selection = analysis_selection(architecture, analysis)
        except ValueError as error:
            plans.append(
                AnalysisPlan(
                    analysis.name,
                    {},
                    "invalid",
                    str(error),
                    configuration=configuration,
                )
            )
            continue
        try:
            resolved, canonical = resolve_selected(
                architecture, analysis, selection
            )
        except ValueError as error:
            plans.append(
                AnalysisPlan(
                    analysis.name,
                    selection,
                    "invalid",
                    str(error),
                    configuration=configuration,
                )
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
                selection=selection,
                status=status,
                detail=report.detail,
                canonical=canonical,
                report=report,
                configuration=configuration,
            )
        )
    return tuple(plans)
