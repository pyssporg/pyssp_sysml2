"""Resolve SysML variation points into one concrete architecture.

Selection enters from outside SysML: a mapping from a usage path to a variant
name. :func:`resolve` returns a deep copy with each selected variation point
substituted.

Two variation kinds are resolved:

- **Part variation**: the key names a part usage and the selected variant's
  type replaces the usage type. The usage keeps its name and ports, so the SSD
  element name is stable across selections. The point may sit on a definition
  (``variation part def SourceChoice``) or on the usage itself
  (``variation part source : SignalSource { ... }``).
- **Attribute variation**: the key names an attribute usage and the selected
  variant's type replaces the usage type, so parameter binds resolve against
  the selected set.

A variant without a type but with a body (``variant part directPath { part g
: Gain; connect u to g.u; }``) becomes an anonymous part definition synthesized
from that body. It carries the variation point's ports, gets a deterministic
name (``<Point>__<variant>``), and the usage is retyped to it, so generation
emits a subsystem whose subparts and connections come from the body. The
body's parameter-port connections are not emitted as SSD connections; see
``docs/breakdown/02-architecture/generation-pipeline.md``.

A body whose only members are attribute usages and bindings is a statement
container, not a component: its attributes and bindings are merged into the
definition that owns the variation usage, and the usage is removed so no empty
component reaches the SSD.

A selection key is the usage name, dotted for nesting (``source=stepImplementation``,
``scenario=baseline``, ``path.inner=variantName``). A bare name is accepted
only when exactly one reachable usage carries it. Attribute usages are
collected on the composition and on any analysis that composes it, so an
analysis scenario stays selectable when its model is generated.

A variation usage inside a selected body is itself a point. After an outer
selection is applied, inner points are resolved by their full dotted path. An
unselected inner point fails with that path. A third level of nesting raises a
clear ``ValueError`` rather than being flattened. Connect variants and
attribute variants with bodies remain out of scope.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from pyssp_sysml2.parameters.dialect.markers import is_parameter_interface
from pyssp_sysml2.metadata.roles import is_analysis
from pyssp_sysml2.model import (
    Architecture,
    Attribute,
    AttributeDefinition,
    Connection,
    PartDefinition,
    PartUsage,
    PortUsage,
    VariantBody,
    VariantMember,
)

__all__ = [
    "has_variation",
    "refuse_variation_erasure",
    "require_resolved_attribute_variation",
    "resolve",
    "resolve_selected",
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
        if self.variation is not None:
            return self.variation.variants
        return self.usage.variants


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


def _analysis_roots(
    architecture: Architecture, composition: PartDefinition
) -> list[PartDefinition]:
    """The composition plus every analysis that composes it directly."""
    roots = [composition]
    for definition in architecture.part_definitions.values():
        if definition is composition or not is_analysis(architecture, definition):
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
    """Every attribute usage reachable from the composition or a composing analysis.

    This is the *accepted* set: a caller may address any of these usages, so a
    selection map authored for one analysis can be handed to the model build
    unchanged. Required points are scoped by :func:`_target_attribute_records`.
    """
    records: list[_AttributeUsage] = []
    seen_usages: set[tuple[str, str]] = set()
    for root in _analysis_roots(architecture, composition):
        _walk_attribute_records(
            architecture, root, (), frozenset(), seen_usages, records
        )
    return records


def _target_attribute_records(
    architecture: Architecture, composition: PartDefinition
) -> list[_AttributeUsage]:
    """Every attribute usage reachable from *composition* only.

    An analysis target walks its `sut` into the composed model, so both scopes
    are covered. A model target does not require another analysis's scenario
    usage; that is what makes a per-analysis selection map sufficient.
    """
    records: list[_AttributeUsage] = []
    _walk_attribute_records(
        architecture, composition, (), frozenset(), set(), records
    )
    return records


def _walk_attribute_records(
    architecture: Architecture,
    part_def: PartDefinition,
    prefix: tuple[str, ...],
    seen: frozenset[str],
    seen_usages: set[tuple[str, str]],
    records: list[_AttributeUsage],
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
            _walk_attribute_records(
                architecture,
                definition,
                prefix + (part_name,),
                seen,
                seen_usages,
                records,
            )


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
    if record.variation is None and not record.usage_level:
        raise ValueError(
            f"Selection key '{key}' names part usage '{record.key}', which is "
            "not a variation point; select a variation point instead."
        )

    point_name = record.point_name
    if not record.variants:
        raise ValueError(
            f"Variation point '{point_name}' has no captured part variants; "
            "only 'variant part <name> : <PartDef>;' members are supported."
        )
    variant = next(
        (member for member in record.variants if member.name == variant_name),
        None,
    )
    if variant is None:
        names = ", ".join(member.name for member in record.variants) or "none"
        raise ValueError(
            f"Unknown variant '{variant_name}' for variation point "
            f"'{point_name}'; expected one of {names}."
        )
    if variant.kind != "part":
        raise ValueError(
            f"Selected variant '{variant_name}' of variation point '{point_name}' "
            f"is a '{variant.kind}' variant; only part variants are supported."
        )
    if variant.body is not None and variant.type_name is not None:
        raise ValueError(
            f"Selected variant '{variant_name}' of variation point '{point_name}' "
            f"declares both type '{variant.type_name}' and a body; use one."
        )
    if variant.body is None:
        if variant.type_name is None:
            raise ValueError(
                f"Selected variant '{variant_name}' of variation point "
                f"'{point_name}' has no resolvable type and no body; write "
                f"'variant part {variant_name} : <PartDef>;' or give it a body."
            )
        if variant.type_name not in architecture.part_definitions:
            raise ValueError(
                f"Selected variant '{variant_name}' of variation point "
                f"'{point_name}' has type '{variant.type_name}', which is not a "
                "part definition; only part variants are supported."
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


def _body_definition(
    record: _Usage,
    variant: VariantMember,
    architecture: Architecture,
) -> PartDefinition:
    """Synthesize the anonymous part definition a variant body declares.

    The definition carries the variation point's ports and the body's own
    subparts and connections. The body's attributes and bindings belong to the
    definition that owns the variation usage and are merged there by
    :func:`_merge_body`. Parameter-port connections are kept on the captured
    body but not copied: the SSD represents parameter application with binds
    and mappings, not with connections.
    """
    body = variant.body
    assert body is not None

    point = record.variation if record.variation is not None else record.definition
    ports = copy.deepcopy(point.ports) if point is not None else {}
    for connection in body.connections.values():
        _check_body_connection(record, variant, body, connection, ports)

    _reject_third_level(record, variant, body, architecture)

    if record.variation is not None:
        name = f"{record.variation.name}__{variant.name}"
    else:
        name = f"{record.owner.name}__{record.usage.name}__{variant.name}"
    if name in architecture.part_definitions:
        raise ValueError(
            f"Synthesized variant definition '{name}' for variation point "
            f"'{record.point_name}' collides with an existing part definition; "
            "rename the variant."
        )
    return PartDefinition(
        name=name,
        source_file=point.source_file if point is not None else None,
        ports=ports,
        parts=copy.deepcopy(body.parts),
        connections={
            key: connection
            for key, connection in body.connections.items()
            if not _touches_parameter_port(body, connection, ports, architecture)
        },
    )


def _reject_third_level(
    record: _Usage,
    variant: VariantMember,
    body: VariantBody,
    architecture: Architecture,
) -> None:
    """Refuse a variation point nested three levels deep instead of flattening.

    The selected body of an outer point may carry one inner point, keyed
    ``outer.inner``. A point inside that inner point's selected body would need
    ``outer.inner.innermost`` and is out of scope.
    """
    if len(record.path) < 2:
        return
    for usage in body.parts.values():
        definition = architecture.resolve_part(usage)
        if usage.is_variation or (
            definition is not None and definition.is_variation
        ):
            raise ValueError(
                f"Variant '{variant.name}' of variation point "
                f"'{record.point_name}' at '{record.key}' declares variation "
                "point "
                f"'{usage.name}'; variation nested deeper than two levels is "
                "not supported."
            )


def _merge_body(
    record: _Usage,
    variant: VariantMember,
    body: VariantBody,
) -> None:
    """Merge a selected body's attributes and bindings into its owning definition."""
    owner = record.owner
    for name, attribute in body.attributes.items():
        if name in owner.attributes:
            raise ValueError(
                f"Variant '{variant.name}' of variation point "
                f"'{record.point_name}' declares attribute '{name}', which "
                f"definition '{owner.name}' already declares; rename it."
            )
        owner.attributes[name] = copy.deepcopy(attribute)
    for binding in body.bindings:
        owner.bindings.append(copy.deepcopy(binding))


def _check_body_connection(
    record: _Usage,
    variant: VariantMember,
    body: VariantBody,
    connection: Connection,
    ports: dict[str, PortUsage],
) -> None:
    """Reject a body connection that leaves the point's declared interface."""
    for part_name, port_name in (
        (connection.source_part, connection.source_port),
        (connection.destination_part, connection.destination_port),
    ):
        if part_name is None:
            if port_name not in ports:
                raise ValueError(
                    f"Variant '{variant.name}' of variation point "
                    f"'{record.point_name}' connects to port '{port_name}', "
                    "which the point does not declare; declare it as a port of "
                    "the variation point."
                )
        elif part_name not in body.parts:
            raise ValueError(
                f"Variant '{variant.name}' of variation point "
                f"'{record.point_name}' connects to part '{part_name}', which "
                "its body does not declare."
            )


def _touches_parameter_port(
    body: VariantBody,
    connection: Connection,
    ports: dict[str, PortUsage],
    architecture: Architecture,
) -> bool:
    """True when either end of *connection* is a parameter-interface port."""
    return any(
        _is_parameter_endpoint(body, part_name, port_name, ports, architecture)
        for part_name, port_name in (
            (connection.source_part, connection.source_port),
            (connection.destination_part, connection.destination_port),
        )
    )


def _is_parameter_endpoint(
    body: VariantBody,
    part_name: str | None,
    port_name: str,
    ports: dict[str, PortUsage],
    architecture: Architecture,
) -> bool:
    if part_name is None:
        port_usage = ports.get(port_name)
    else:
        part = body.parts.get(part_name)
        definition = architecture.resolve_part(part) if part is not None else None
        port_usage = (
            definition.ports.get(port_name) if definition is not None else None
        )
    if port_usage is None:
        return False
    port_definition = architecture.resolve_port(port_usage)
    return port_definition is not None and is_parameter_interface(port_definition)


def require_resolved_attribute_variation(
    architecture: Architecture, composition: PartDefinition
) -> None:
    """Reject generation while an attribute variation point is unselected."""
    remaining = [
        record
        for record in _target_attribute_records(architecture, composition)
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

    See :func:`resolve_selected`; this wrapper drops the canonical selection map.
    """
    return resolve_selected(architecture, composition, selections)[0]


def resolve_selected(
    architecture: Architecture,
    composition: str | PartDefinition,
    selections: Mapping[str, str] | None = None,
) -> tuple[Architecture, dict[str, str]]:
    """Return a resolved copy and the canonical selection map it was built from.

    ``composition`` is a part definition or its name. Each key in
    ``selections`` names a part or attribute usage reachable from that
    composition; each value names one variant of the variation point at that
    usage. An unknown, ambiguous, non-point, or unselected key raises
    ``ValueError``.

    The returned map is keyed by the usage path as it exists in the target
    composition (``source`` for a model, ``sut.source`` for an analysis). Pass
    it to :func:`pyssp_sysml2.parameters.constraints.evaluate` so constraint
    bindings resolve against the same keys the variation points used.

    Keys are applied outermost first. Selecting an outer body can introduce an
    inner variation point, which the next pass finds at its full dotted path
    (``path.inner=variant``).
    """
    name = (
        composition.name
        if isinstance(composition, PartDefinition)
        else composition
    )
    source = architecture.get_part_def(name)

    resolved = copy.deepcopy(architecture)
    resolved_source = resolved.get_part_def(source.name)
    pending = dict(selections or {})
    applied: list[tuple[_Usage | _AttributeUsage, VariantMember, bool]] = []
    canonical: dict[str, str] = {}

    while pending:
        part_records = _usage_records(resolved, resolved_source)
        attribute_records = _attribute_records(resolved, resolved_source)
        progressed = False
        for key in sorted(pending, key=lambda item: (item.count("."), item)):
            try:
                record = _lookup(
                    part_records, attribute_records, key, resolved_source
                )
            except ValueError:
                if any(
                    other != key and key.startswith(other + ".")
                    for other in pending
                ):
                    continue
                raise
            variant = _choice(
                record, key, pending[key], resolved, resolved_source
            )
            removed = _apply(resolved, record, variant)
            applied.append((record, variant, removed))
            canonical[record.key] = pending[key]
            del pending[key]
            progressed = True
            break
        if not progressed:
            key = min(pending, key=lambda item: (item.count("."), item))
            raise _unknown_key(key, resolved_source)

    final_parts = _usage_records(resolved, resolved_source)
    final_part_keys = {record.key for record in final_parts}
    final_attributes = _attribute_records(resolved, resolved_source)
    final_attribute_keys = {record.key for record in final_attributes}
    for record, _, removed in applied:
        if removed:
            continue
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
        record
        for record in _target_attribute_records(resolved, resolved_source)
        if record.is_point
    ]
    if remaining_attributes:
        raise _missing_attribute(remaining_attributes[0], resolved_source)
    return resolved, canonical


def _apply(
    resolved: Architecture,
    record: _Usage | _AttributeUsage,
    variant: VariantMember,
) -> bool:
    """Apply one selection in place; return True when it removes the usage.

    A body with neither parts nor connections is a statement container: its
    attributes and bindings are merged into the owning definition and the
    variation usage itself is removed, so no empty component reaches the SSD.
    A body with parts or connections is a component definition and keeps the
    usage.
    """
    if isinstance(record, _AttributeUsage):
        record.usage.type_name = variant.type_name
        return False

    body = variant.body
    if body is not None:
        _merge_body(record, variant, body)
        if not body.parts and not body.connections:
            record.owner.parts.pop(record.usage.name, None)
            return True
        definition = _body_definition(record, variant, resolved)
        resolved.add_part_def(definition)
        record.usage.type_name = definition.name
    else:
        record.usage.type_name = variant.type_name
    record.usage.is_variation = False
    return False
