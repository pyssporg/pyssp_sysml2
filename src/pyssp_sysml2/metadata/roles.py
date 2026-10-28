"""Role markers for exportable models, studies, and experiments.

The marker definitions are ordinary SysML definitions in the model package::

    part def SspModel;
    part def Study;

    attribute def Experiment {
      attribute startTime : Real;
      attribute stopTime : Real;
      attribute stepSize : Real;
      attribute tolerance : Real;
    }

A composition is exportable when its ``part def`` specializes ``SspModel``. A
study specializes ``Study`` and composes the exported model through a single
part usage, conventionally named ``sut``. Studies are never exported as SSPs.
"""

from __future__ import annotations

from dataclasses import dataclass

from pyssp_sysml2.model import (
    Architecture,
    Attribute,
    AttributeDefinition,
    PartDefinition,
    PartUsage,
)

SSP_MODEL_MARKER = "SspModel"
STUDY_MARKER = "Study"
EXPERIMENT_MARKER = "Experiment"

EXPERIMENT_FIELDS = ("startTime", "stopTime", "stepSize")


@dataclass(frozen=True)
class Experiment:
    """One resolved study experiment.

    Tolerance is not part of the experiment: it is a property of the composed
    FMUs and is read from their model descriptions by the simulation stage.
    """

    name: str
    start_time: float
    stop_time: float
    step_size: float


def _short_name(name: str) -> str:
    return name.split("::")[-1]


def _specializes_marker(
    architecture: Architecture,
    definition: PartDefinition | AttributeDefinition | None,
    marker: str,
    seen: set[str] | None = None,
) -> bool:
    if definition is None:
        return False
    if _short_name(definition.name) == marker:
        return True
    seen = set() if seen is None else seen
    if definition.name in seen:
        return False
    seen.add(definition.name)
    for supertype in definition.specializes:
        if _short_name(supertype) == marker:
            return True
        base: PartDefinition | AttributeDefinition | None
        if isinstance(definition, PartDefinition):
            base = architecture.part_definitions.get(_short_name(supertype))
        else:
            base = architecture.attribute_definitions.get(_short_name(supertype))
        if _specializes_marker(architecture, base, marker, seen):
            return True
    return False


def is_ssp_model(architecture: Architecture, definition: PartDefinition) -> bool:
    return _specializes_marker(architecture, definition, SSP_MODEL_MARKER)


def is_study(architecture: Architecture, definition: PartDefinition) -> bool:
    return _specializes_marker(architecture, definition, STUDY_MARKER)


def is_experiment_definition(
    architecture: Architecture, definition: AttributeDefinition | None
) -> bool:
    return _specializes_marker(architecture, definition, EXPERIMENT_MARKER)


def _variation_point(
    architecture: Architecture,
    definition: PartDefinition | None,
    seen: set[str] | None = None,
) -> str | None:
    """Name of the first variation point reachable from a composition, or None.

    A point is either a variation definition used by a part, or a part usage
    that is itself a variation point (``variation part source : S;``).
    """
    if definition is None:
        return None
    if definition.is_variation:
        return definition.name
    seen = set() if seen is None else seen
    if definition.name in seen:
        return None
    seen.add(definition.name)
    for usage in definition.parts.values():
        if usage.is_variation:
            return usage.name
        found = _variation_point(architecture, architecture.resolve_part(usage), seen)
        if found is not None:
            return found
    return None


def require_resolved_variation(
    architecture: Architecture, composition: PartDefinition
) -> None:
    """Reject generation of a composition that still carries a variation point.

    Generation is called without a selection here, so the point cannot be
    resolved and a variant-less artifact would be emitted silently. Reject
    instead and name the point; the caller passes ``--select`` to resolve it
    (IMP-006).
    """
    point = _variation_point(architecture, composition)
    if point is None:
        return
    raise ValueError(
        f"Variation point '{point}' in composition '{composition.name}' is not "
        "selected; pass a selection for it (for example "
        f"--select <usage>=<variant>)."
    )


def validate_role_markers(architecture: Architecture) -> None:
    """Reject marker use when the marker definition is missing."""
    used = {
        _short_name(name)
        for definition in architecture.part_definitions.values()
        for name in definition.specializes
        if _short_name(name) in {SSP_MODEL_MARKER, STUDY_MARKER}
    }
    for marker in sorted(used):
        if marker not in architecture.part_definitions:
            raise ValueError(
                f"Role marker '{marker}' is used but not defined. Add "
                f"'part def {marker};' to the package."
            )


def exportable_part_definitions(architecture: Architecture) -> list[PartDefinition]:
    return [
        definition
        for definition in architecture.part_definitions.values()
        if is_ssp_model(architecture, definition)
    ]


def study_part_definitions(architecture: Architecture) -> list[PartDefinition]:
    return [
        definition
        for definition in architecture.part_definitions.values()
        if is_study(architecture, definition)
    ]


def model_usage(
    architecture: Architecture, study: PartDefinition
) -> tuple[PartUsage, PartDefinition]:
    """The single exportable model usage composed by a study."""
    usages: list[tuple[PartUsage, PartDefinition]] = []
    for usage in study.parts.values():
        definition = architecture.resolve_part(usage)
        if definition is None:
            raise ValueError(
                f"Unresolved part definition for {study.name}.{usage.name}"
            )
        if is_ssp_model(architecture, definition):
            usages.append((usage, definition))
    if len(usages) != 1:
        names = ", ".join(usage.name for usage, _ in usages) or "none"
        raise ValueError(
            f"Study '{study.name}' must compose exactly one SspModel part; "
            f"found {names}"
        )
    return usages[0]


def _effective_members(
    architecture: Architecture,
    definition: AttributeDefinition,
    seen: set[str] | None = None,
) -> dict[str, Attribute]:
    seen = set() if seen is None else seen
    if definition.name in seen:
        return {}
    seen.add(definition.name)

    members: dict[str, Attribute] = {}
    for supertype in definition.specializes:
        base = architecture.attribute_definitions.get(_short_name(supertype))
        if base is not None:
            members.update(_effective_members(architecture, base, seen))
    for name, attribute in definition.attributes.items():
        inherited = members.get(name)
        if (
            attribute.value is None
            and inherited is not None
            and inherited.value is not None
        ):
            members[name] = inherited
        else:
            members[name] = attribute
    return members


def experiment_attribute(
    architecture: Architecture, study: PartDefinition
) -> tuple[str, Attribute, AttributeDefinition]:
    """The single experiment attribute declared by a study."""
    found: list[tuple[str, Attribute, AttributeDefinition]] = []
    for name, attribute in study.attributes.items():
        definition = architecture.resolve_attribute_def(attribute)
        if is_experiment_definition(architecture, definition):
            assert definition is not None
            found.append((name, attribute, definition))
    if len(found) != 1:
        names = ", ".join(name for name, _, _ in found) or "none"
        raise ValueError(
            f"Study '{study.name}' must declare exactly one Experiment "
            f"attribute; found {names}"
        )
    return found[0]


def read_experiment(
    architecture: Architecture, study: PartDefinition
) -> Experiment:
    name, _attribute, definition = experiment_attribute(architecture, study)
    members = _effective_members(architecture, definition)
    values: dict[str, float] = {}
    for field in EXPERIMENT_FIELDS:
        attribute = members.get(field)
        if attribute is None or attribute.value is None:
            raise ValueError(
                f"Experiment '{definition.name}.{field}' must have a numeric value"
            )
        value = attribute.value
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(
                f"Experiment '{definition.name}.{field}' must be numeric, got "
                f"{attribute.primitive_type_str()}"
            )
        values[field] = float(value)

    if values["stopTime"] <= values["startTime"]:
        raise ValueError(
            f"Experiment '{definition.name}' stopTime must be greater than startTime"
        )
    if values["stepSize"] <= 0:
        raise ValueError(f"Experiment '{definition.name}' stepSize must be positive")

    return Experiment(
        name=name,
        start_time=values["startTime"],
        stop_time=values["stopTime"],
        step_size=values["stepSize"],
    )
