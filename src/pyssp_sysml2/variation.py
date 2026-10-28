"""Resolve SysML variation points into one concrete architecture.

Selection enters from outside SysML: a mapping from a part-usage path inside
the composition to a variant name. :func:`resolve` returns a deep copy with
each selected variation point substituted. The usage keeps its name and ports,
so the SSD element name is stable across selections; only the usage type
changes to the selected variant's type.

A selection key is the part-usage name, dotted for nesting
(``source=stepImplementation``, ``path.inner=variantName``). A bare name is
accepted only when exactly one reachable usage carries it.

Usage-level variation, attribute variation, variant bodies, and connect or
bind variants are out of scope and raise ``ValueError`` rather than producing
a partial artifact.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass

from pyssp_sysml2.sysml_model import (
    Architecture,
    PartDefinition,
    PartUsage,
    VariantMember,
)

__all__ = ["resolve"]


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


def _reject_attribute_variation(
    architecture: Architecture, part_def: PartDefinition
) -> None:
    for name, attribute in part_def.attributes.items():
        definition = architecture.resolve_attribute_def(attribute)
        if definition is None or not definition.is_variation:
            continue
        raise ValueError(
            f"Attribute variation point '{definition.name}' is used by "
            f"'{part_def.name}.{name}'; attribute variation is out of scope. "
            "Replace it with a fixed attribute definition."
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
        _reject_attribute_variation(architecture, part_def)
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


def _unknown_key(key: str, composition: PartDefinition) -> ValueError:
    return ValueError(
        f"Unknown selection key '{key}' in composition '{composition.name}'; "
        "name a part usage by its path, for example "
        "source=stepImplementation."
    )


def _lookup(
    records: list[_Usage], key: str, composition: PartDefinition
) -> _Usage:
    """The usage a selection key names; bare keys must be unambiguous."""
    if "." in key:
        exact = [record for record in records if record.key == key]
        if exact:
            return exact[0]
        raise _unknown_key(key, composition)
    matches = [record for record in records if record.path[-1] == key]
    if not matches:
        raise _unknown_key(key, composition)
    if len(matches) > 1:
        paths = ", ".join(f"'{record.key}'" for record in matches)
        raise ValueError(
            f"Selection key '{key}' is ambiguous in composition "
            f"'{composition.name}'; it names {paths}. Write the full dotted path."
        )
    return matches[0]


def _usage_level_error(key: str, composition: PartDefinition) -> ValueError:
    return ValueError(
        f"Selection key '{key}' names usage-level variation point '{key}'; "
        "usage-level variation is not supported. Move 'variation' to a part "
        "definition and select the usage typed by it."
    )


def _choice(
    record: _Usage,
    key: str,
    variant_name: str,
    architecture: Architecture,
    composition: PartDefinition,
) -> VariantMember:
    """Validate one selection against its variation point and return its variant."""
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


def _missing(record: _Usage, composition: PartDefinition) -> ValueError:
    if record.usage_level:
        return _usage_level_error(record.key, composition)
    return ValueError(
        f"Variation point '{record.point_name}' at '{record.key}' in "
        f"composition '{composition.name}' is not selected; pass "
        f"{record.key}=<variant>."
    )


def resolve(
    architecture: Architecture,
    composition: str | PartDefinition,
    selections: Mapping[str, str] | None = None,
) -> Architecture:
    """Return a deep copy with every selected variation point substituted.

    ``composition`` is a part definition or its name. Each key in
    ``selections`` names a part usage reachable from that composition; each
    value names one variant of the variation point at that usage. An unknown,
    ambiguous, non-point, or unselected key raises ``ValueError``.
    """
    name = (
        composition.name
        if isinstance(composition, PartDefinition)
        else composition
    )
    source = architecture.get_part_def(name)

    records = _usage_records(architecture, source)
    choices: list[tuple[_Usage, VariantMember]] = []
    for key, variant_name in dict(selections or {}).items():
        record = _lookup(records, key, source)
        choices.append(
            (
                record,
                _choice(record, key, variant_name, architecture, source),
            )
        )

    resolved = copy.deepcopy(architecture)
    resolved_source = resolved.get_part_def(source.name)
    resolved_records = {
        record.key: record for record in _usage_records(resolved, resolved_source)
    }
    for record, variant in choices:
        target = resolved_records.get(record.key)
        if target is None:
            raise ValueError(
                f"Selection key '{record.key}' no longer resolves after "
                "resolution; select one variation point per path."
            )
        target.usage.type_name = variant.type_name
        target.usage.is_variation = False

    final_records = _usage_records(resolved, resolved_source)
    final_keys = {record.key for record in final_records}
    for record, _ in choices:
        if record.key not in final_keys:
            raise ValueError(
                f"Selection key '{record.key}' is nested under another selected "
                "variation point and no longer exists after resolution; select "
                "one variation point per path."
            )
    remaining = [record for record in final_records if record.is_point]
    if remaining:
        raise _missing(remaining[0], resolved_source)
    return resolved
