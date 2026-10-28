"""Resolve SysML variation points into one concrete architecture.

Selection enters from outside SysML: a mapping from a usage path to a variant
name. :func:`resolve` returns a deep copy with each selected variation point
substituted.

Two variation kinds are resolved:

- **Part variation**: the key names a part usage and the selected variant's
  type replaces the usage type. The usage keeps its name and ports, so the SSD
  element name is stable across selections.
- **Attribute variation**: the key names an attribute usage and the selected
  variant's type replaces the usage type, so parameter binds resolve against
  the selected set.

A selection key is the usage name, dotted for nesting (``source=stepImplementation``,
``scenario=baseline``, ``path.inner=variantName``). A bare name is accepted
only when exactly one reachable usage carries it. Attribute usages are
collected on the composition and on any study that composes it, so a study
scenario stays selectable when its model is generated.

Usage-level variation, variant bodies, and connect or bind variants are out of
scope and raise ``ValueError`` rather than producing a partial artifact.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from pyssp_sysml2.roles import is_study
from pyssp_sysml2.sysml_model import (
    Architecture,
    Attribute,
    AttributeDefinition,
    PartDefinition,
    PartUsage,
    VariantMember,
)

__all__ = [
    "has_variation",
    "refuse_variation_erasure",
    "require_resolved_attribute_variation",
    "resolve",
]


@dataclass(frozen=True)
class _Usage:
    """One reachable part usage, with the variation facts around it."""

    path: tuple[str, ...]
    owner: PartDefinition
    usage: PartUsage
    definition: PartDefinition | None
    variation: PartDefinition | None
    usage_level: bool

    @property
    def key(self) -> str:
        return ".".join(self.path)

    @property
    def is_point(self) -> bool:
        return self.usage_level or self.variation is not None

    @property
    def point_name(self) -> str:
        return self.variation.name if self.variation is not None else self.usage.name

    @property
    def variants(self) -> list[VariantMember]:
        return self.variation.variants if self.variation is not None else []


@dataclass(frozen=True)
class _AttributeUsage:
    """One reachable attribute usage, with the variation facts around it."""

    owner_name: str
    path: tuple[str, ...]
    name: str
    usage: Attribute
    definition: AttributeDefinition | None
    variation: AttributeDefinition | None

    @property
    def key(self) -> str:
        return ".".join(self.path)

    @property
    def is_point(self) -> bool:
        return self.variation is not None

    @property
    def point_name(self) -> str:
        return self.variation.name if self.variation is not None else self.name

    @property
    def variants(self) -> list[VariantMember]:
        return self.variation.variants if self.variation is not None else []


def _variation_names(architecture: Architecture) -> list[str]:
    """Names of every variation point the architecture carries, sorted."""
    points: set[str] = set()
    for part_def in architecture.part_definitions.values():
        if part_def.is_variation or part_def.variants:
            points.add(part_def.name)
        for usage in part_def.parts.values():
            if usage.is_variation:
                points.add(f"{part_def.name}.{usage.name}")

    definitions = [
        *architecture.part_definitions.values(),
        *architecture.port_definitions.values(),
        *architecture.attribute_definitions.values(),
    ]
    for definition in definitions:
        for name, attribute in definition.attributes.items():
            attribute_def = architecture.resolve_attribute_def(attribute)
            if attribute_def is not None and attribute_def.is_variation:
                points.add(f"{definition.name}.{name}")

    for attribute_def in architecture.attribute_definitions.values():
        if attribute_def.is_variation or attribute_def.variants:
            points.add(attribute_def.name)
    return sorted(points)


def has_variation(architecture: Architecture) -> bool:
    """Whether the architecture declares any variation point or variant member.

    Covers variation part and attribute definitions, variation part usages, and
    attribute usages typed by a variation attribute definition.
    """
    return bool(_variation_names(architecture))


def refuse_variation_erasure(
    architecture: Architecture, target: str | Path
) -> None:
    """Raise when rewriting *target* would drop variation points.

    SysML export emits only the documented simulation dialect, so a variation
    point or variant member has no representation and would vanish silently.
    """
    names = _variation_names(architecture)
    if not names:
        return
    listed = ", ".join(f"'{name}'" for name in names)
    raise ValueError(
        "SysML export does not represent variation points; writing "
        f"'{target}' would erase {listed}. Remove the variation points or "
        "keep the authored architecture."
    )


def _usage_records(
    architecture: Architecture, composition: PartDefinition
) -> list[_Usage]:
    """Every part usage reachable from *composition*, in declaration order."""
    records: list[_Usage] = []

    def walk(
        part_def: PartDefinition, prefix: tuple[str, ...], seen: frozenset[str]
    ) -> None:
        if part_def.name in seen:
            return
        seen = seen | {part_def.name}
        for name, usage in part_def.parts.items():
            path = prefix + (name,)
            definition = architecture.resolve_part(usage)
            variation = (
                definition
                if definition is not None and definition.is_variation
                else None
            )
            records.append(
                _Usage(
                    path=path,
                    owner=part_def,
                    usage=usage,
                    definition=definition,
                    variation=variation,
                    usage_level=usage.is_variation,
                )
            )
            if definition is not None:
                walk(definition, path, seen)

    walk(composition, (), frozenset())
    return records


def _study_roots(
    architecture: Architecture, composition: PartDefinition
) -> list[PartDefinition]:
    """The composition plus every study that composes it directly."""
    roots = [composition]
    for definition in architecture.part_definitions.values():
        if definition is composition or not is_study(architecture, definition):
            continue
        if any(
            architecture.resolve_part(usage) is composition
            for usage in definition.parts.values()
        ):
            roots.append(definition)
    return roots


def _attribute_records(
    architecture: Architecture, composition: PartDefinition
) -> list[_AttributeUsage]:
    """Every attribute usage reachable from the composition or a composing study."""
    records: list[_AttributeUsage] = []
    seen_usages: set[tuple[str, str]] = set()

    def walk(
        part_def: PartDefinition, prefix: tuple[str, ...], seen: frozenset[str]
    ) -> None:
        if part_def.name in seen:
            return
        seen = seen | {part_def.name}
        for name, attribute in part_def.attributes.items():
            identity = (part_def.name, name)
            if identity in seen_usages:
                continue
            seen_usages.add(identity)
            definition = architecture.resolve_attribute_def(attribute)
            records.append(
                _AttributeUsage(
                    owner_name=part_def.name,
                    path=prefix + (name,),
                    name=name,
                    usage=attribute,
                    definition=definition,
                    variation=(
                        definition
                        if definition is not None and definition.is_variation
                        else None
                    ),
                )
            )
        for part_name, usage in part_def.parts.items():
            definition = architecture.resolve_part(usage)
            if definition is not None:
                walk(definition, prefix + (part_name,), seen)

    for root in _study_roots(architecture, composition):
        walk(root, (), frozenset())
    return records


def _unknown_key(key: str, composition: PartDefinition) -> ValueError:
    return ValueError(
        f"Unknown selection key '{key}' in composition '{composition.name}'; "
        "name a part or attribute usage by its path, for example "
        "source=stepImplementation or scenario=baseline."
    )


def _ambiguous(
    key: str,
    composition: PartDefinition,
    records: list[_Usage | _AttributeUsage],
) -> ValueError:
    paths = ", ".join(f"'{record.key}'" for record in records)
    return ValueError(
        f"Selection key '{key}' is ambiguous in composition "
        f"'{composition.name}'; it names {paths}. Write the full dotted path."
    )


def _lookup(
    part_records: list[_Usage],
    attribute_records: list[_AttributeUsage],
    key: str,
    composition: PartDefinition,
) -> _Usage | _AttributeUsage:
    """The usage a selection key names; bare keys must be unambiguous."""
    records: list[_Usage | _AttributeUsage] = [*part_records, *attribute_records]
    if "." in key:
        exact = [record for record in records if record.key == key]
        if len(exact) > 1:
            raise _ambiguous(key, composition, exact)
        if exact:
            return exact[0]
        raise _unknown_key(key, composition)
    matches = [record for record in records if record.path[-1] == key]
    if not matches:
        raise _unknown_key(key, composition)
    if len(matches) > 1:
        raise _ambiguous(key, composition, matches)
    return matches[0]


def _usage_level_error(key: str, composition: PartDefinition) -> ValueError:
    return ValueError(
        f"Selection key '{key}' names usage-level variation point '{key}'; "
        "usage-level variation is not supported. Move 'variation' to a part "
        "definition and select the usage typed by it."
    )


def _choice(
    record: _Usage | _AttributeUsage,
    key: str,
    variant_name: str,
    architecture: Architecture,
    composition: PartDefinition,
) -> VariantMember:
    """Validate one selection against its variation point and return its variant."""
    if isinstance(record, _AttributeUsage):
        return _attribute_choice(
            record, key, variant_name, architecture, composition
        )
    return _part_choice(record, key, variant_name, architecture, composition)


def _part_choice(
    record: _Usage,
    key: str,
    variant_name: str,
    architecture: Architecture,
    composition: PartDefinition,
) -> VariantMember:
    """Validate one part selection and return its variant."""
    if record.usage_level:
        raise _usage_level_error(key, composition)
    if record.variation is None:
        raise ValueError(
            f"Selection key '{key}' names part usage '{record.key}', which is "
            "not a variation point; select a variation point instead."
        )

    point = record.variation
    if not point.variants:
        raise ValueError(
            f"Variation point '{point.name}' has no captured part variants; "
            "only 'variant part <name> : <PartDef>;' members are supported."
        )
    variant = next(
        (member for member in point.variants if member.name == variant_name), None
    )
    if variant is None:
        names = ", ".join(member.name for member in point.variants) or "none"
        raise ValueError(
            f"Unknown variant '{variant_name}' for variation point "
            f"'{point.name}'; expected one of {names}."
        )
    if variant.kind != "part":
        raise ValueError(
            f"Selected variant '{variant_name}' of variation point '{point.name}' "
            f"is a '{variant.kind}' variant; only part variants are supported."
        )
    if variant.type_name is None:
        raise ValueError(
            f"Selected variant '{variant_name}' of variation point '{point.name}' "
            "has no resolvable type; variant bodies are not supported. Write "
            f"'variant part {variant_name} : <PartDef>;'."
        )
    if variant.type_name not in architecture.part_definitions:
        raise ValueError(
            f"Selected variant '{variant_name}' of variation point '{point.name}' "
            f"has type '{variant.type_name}', which is not a part definition; "
            "only part variants are supported."
        )
    return variant


def _attribute_choice(
    record: _AttributeUsage,
    key: str,
    variant_name: str,
    architecture: Architecture,
    composition: PartDefinition,
) -> VariantMember:
    """Validate one attribute selection and return its variant."""
    if record.variation is None:
        raise ValueError(
            f"Selection key '{key}' names attribute usage '{record.key}', which "
            "is not a variation point; select a variation point instead."
        )

    point = record.variation
    if not point.variants:
        raise ValueError(
            f"Attribute variation point '{point.name}' has no captured attribute "
            "variants; only 'variant attribute <name> : <AttributeDef>;' members "
            "are supported."
        )
    variant = next(
        (member for member in point.variants if member.name == variant_name), None
    )
    if variant is None:
        names = ", ".join(member.name for member in point.variants) or "none"
        raise ValueError(
            f"Unknown variant '{variant_name}' for variation point "
            f"'{point.name}'; expected one of {names}."
        )
    if variant.kind != "attribute":
        raise ValueError(
            f"Selected variant '{variant_name}' of variation point '{point.name}' "
            f"is a '{variant.kind}' variant; only attribute variants are "
            "supported."
        )
    if variant.type_name is None:
        raise ValueError(
            f"Selected variant '{variant_name}' of variation point '{point.name}' "
            "has no resolvable type; variant bodies are not supported. Write "
            f"'variant attribute {variant_name} : <AttributeDef>;'."
        )
    if variant.type_name not in architecture.attribute_definitions:
        raise ValueError(
            f"Selected variant '{variant_name}' of variation point '{point.name}' "
            f"has type '{variant.type_name}', which is not an attribute "
            "definition; only attribute variants are supported."
        )
    return variant


def _missing(record: _Usage, composition: PartDefinition) -> ValueError:
    if record.usage_level:
        return _usage_level_error(record.key, composition)
    return ValueError(
        f"Variation point '{record.point_name}' at '{record.key}' in "
        f"composition '{composition.name}' is not selected; pass "
        f"{record.key}=<variant>."
    )


def _missing_attribute(
    record: _AttributeUsage, composition: PartDefinition
) -> ValueError:
    return ValueError(
        f"Attribute variation point '{record.point_name}' at '{record.key}' in "
        f"composition '{composition.name}' is not selected; pass "
        f"{record.key}=<variant>."
    )


def require_resolved_attribute_variation(
    architecture: Architecture, composition: PartDefinition
) -> None:
    """Reject generation while an attribute variation point is unselected."""
    remaining = [
        record
        for record in _attribute_records(architecture, composition)
        if record.is_point
    ]
    if remaining:
        raise _missing_attribute(remaining[0], composition)


def resolve(
    architecture: Architecture,
    composition: str | PartDefinition,
    selections: Mapping[str, str] | None = None,
) -> Architecture:
    """Return a deep copy with every selected variation point substituted.

    ``composition`` is a part definition or its name. Each key in
    ``selections`` names a part or attribute usage reachable from that
    composition; each value names one variant of the variation point at that
    usage. An unknown, ambiguous, non-point, or unselected key raises
    ``ValueError``.
    """
    name = (
        composition.name
        if isinstance(composition, PartDefinition)
        else composition
    )
    source = architecture.get_part_def(name)

    part_records = _usage_records(architecture, source)
    attribute_records = _attribute_records(architecture, source)
    choices: list[tuple[_Usage | _AttributeUsage, VariantMember]] = []
    for key, variant_name in dict(selections or {}).items():
        record = _lookup(part_records, attribute_records, key, source)
        choices.append(
            (
                record,
                _choice(record, key, variant_name, architecture, source),
            )
        )

    resolved = copy.deepcopy(architecture)
    resolved_source = resolved.get_part_def(source.name)
    resolved_parts = {
        record.key: record for record in _usage_records(resolved, resolved_source)
    }
    resolved_attributes = {
        (record.owner_name, record.name): record
        for record in _attribute_records(resolved, resolved_source)
    }
    for record, variant in choices:
        if isinstance(record, _AttributeUsage):
            target = resolved_attributes.get((record.owner_name, record.name))
            if target is None:
                raise ValueError(
                    f"Selection key '{record.key}' no longer resolves after "
                    "resolution; select one variation point per path."
                )
            target.usage.type_name = variant.type_name
            continue
        target = resolved_parts.get(record.key)
        if target is None:
            raise ValueError(
                f"Selection key '{record.key}' no longer resolves after "
                "resolution; select one variation point per path."
            )
        target.usage.type_name = variant.type_name
        target.usage.is_variation = False

    final_parts = _usage_records(resolved, resolved_source)
    final_part_keys = {record.key for record in final_parts}
    final_attributes = _attribute_records(resolved, resolved_source)
    final_attribute_keys = {record.key for record in final_attributes}
    for record, _ in choices:
        if isinstance(record, _AttributeUsage):
            if record.key not in final_attribute_keys:
                raise ValueError(
                    f"Selection key '{record.key}' is nested under another "
                    "selected variation point and no longer exists after "
                    "resolution; select one variation point per path."
                )
            continue
        if record.key not in final_part_keys:
            raise ValueError(
                f"Selection key '{record.key}' is nested under another selected "
                "variation point and no longer exists after resolution; select "
                "one variation point per path."
            )
    remaining = [record for record in final_parts if record.is_point]
    if remaining:
        raise _missing(remaining[0], resolved_source)
    remaining_attributes = [
        record for record in final_attributes if record.is_point
    ]
    if remaining_attributes:
        raise _missing_attribute(remaining_attributes[0], resolved_source)
    return resolved
