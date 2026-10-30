"""Derive an analysis selection from a model-level SysML v2 configuration.

SysML v2 has variation points and variants but no selection construct. The
standard idiom is a 100% configuration: a part definition specialises the model
and binds each variation usage with a redefinition and a feature value::

    part def StepSystem :> System {
      part :>> source = SourceChoice::step;
    }

An analysis composes the configuration, not the root composition. This module
walks the configuration chain back to the root, replays each binding onto the
effective members, descends into a selected variant's type for nested points,
and returns the canonical ``{"usage path": "variant"}`` map that
:func:`pyssp_sysml2.parameters.variation.resolve_selected` consumes.

Every reachable variation point must be bound. An unbound point is an error,
never a silently unselected artifact.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pyssp_sysml2.metadata.roles import (
    SSP_MODEL_MARKER,
    is_ssp_model,
    model_usage,
)
from pyssp_sysml2.model import (
    Architecture,
    Attribute,
    PartDefinition,
    PartUsage,
    VariantBody,
    VariantMember,
)

__all__ = [
    "configuration_name",
    "derived_selection",
    "model_root",
    "scope_analysis_to_root",
]


def _short(name: str) -> str:
    return name.split("::")[-1].strip()


def _definition(
    architecture: Architecture, analysis: PartDefinition | str
) -> PartDefinition:
    if isinstance(analysis, PartDefinition):
        return analysis
    return architecture.get_part_def(analysis)


def _specialization_chain(
    architecture: Architecture, definition: PartDefinition
) -> list[PartDefinition]:
    """Every definition from the root composition down to *definition*."""
    chain = [definition]
    current = definition
    while True:
        base = _model_supertype(architecture, current)
        if base is None:
            break
        chain.append(base)
        current = base
    chain.reverse()
    return chain


def _model_supertype(
    architecture: Architecture, definition: PartDefinition
) -> PartDefinition | None:
    """The single ``SspModel`` supertype, or ``None`` at the root boundary."""
    if _short(definition.name) == SSP_MODEL_MARKER:
        return None
    names = [_short(name) for name in definition.specializes]
    if SSP_MODEL_MARKER in names:
        return None
    bases = []
    others = []
    for name in names:
        base = architecture.part_definitions.get(name)
        if base is None:
            continue
        if is_ssp_model(architecture, base):
            bases.append(base)
        else:
            others.append(base)
    if len(bases) > 1:
        names = ", ".join(base.name for base in bases)
        raise ValueError(
            f"Definition '{definition.name}' specialises more than one SspModel "
            f"definition ({names}); a configuration chain must be linear."
        )
    if not bases and others:
        raise ValueError(
            f"Definition '{definition.name}' specialises '{others[0].name}', "
            "which is not marked SspModel; a configuration chain must specialise "
            "the root composition."
        )
    return bases[0] if bases else None


def model_root(
    architecture: Architecture, definition: PartDefinition
) -> PartDefinition:
    """The outermost composition a configuration specialises, for example ``System``."""
    return _specialization_chain(architecture, definition)[0]


def configuration_name(
    architecture: Architecture, analysis: PartDefinition | str
) -> str | None:
    """The composed model definition's name unless it is the root composition."""
    definition = _definition(architecture, analysis)
    composed = model_usage(architecture, definition)[1]
    return None if model_root(architecture, composed) is composed else composed.name


def scope_analysis_to_root(
    architecture: Architecture, analysis: PartDefinition | str
) -> PartDefinition:
    """Retype the analysis's ``SspModel`` usage to the root composition.

    Generation stays on the root (IMP-106 option B1): a configuration only
    redefines the family's usages, so its inherited parts, ports, connections,
    and binds live on the root. Mutates *architecture* in place and returns the
    root definition; callers load a private copy first.
    """
    definition = _definition(architecture, analysis)
    usage, composed = model_usage(architecture, definition)
    root = model_root(architecture, composed)
    usage.type_name = root.name
    return root


@dataclass(frozen=True)
class _Point:
    """One variation point in an effective scope."""

    kind: str  # "part" or "attribute"
    variation: str
    variants: tuple[VariantMember, ...]


@dataclass(frozen=True)
class _Binding:
    """One redefinition that binds a point, with the scope its value reads from."""

    usage: PartUsage | Attribute
    local_parts: Mapping[str, PartUsage]
    where: str


def _points(
    architecture: Architecture, scope: PartDefinition
) -> dict[str, _Point]:
    """The variation points an effective scope declares, in declaration order."""
    points: dict[str, _Point] = {}
    for name, usage in scope.parts.items():
        definition = architecture.resolve_part(usage)
        if usage.is_variation and usage.variants:
            points[name] = _Point("part", name, tuple(usage.variants))
        elif definition is not None and definition.is_variation:
            points[name] = _Point(
                "part", definition.name, tuple(definition.variants)
            )
    for name, attribute in scope.attributes.items():
        definition = architecture.resolve_attribute_def(attribute)
        if definition is not None and definition.is_variation:
            points[name] = _Point(
                "attribute", definition.name, tuple(definition.variants)
            )
    return points


def _bindings(
    members: PartDefinition | VariantBody,
    local_parts: Mapping[str, PartUsage],
    where: str,
) -> dict[str, _Binding]:
    """Every redefinition among *members*, keyed by its target feature."""
    bindings: dict[str, _Binding] = {}
    for name, usage in members.parts.items():
        if usage.redefines:
            _single_target(name, usage.redefines, where)
            bindings[name] = _Binding(usage, local_parts, where)
    for name, attribute in members.attributes.items():
        if attribute.redefines:
            _single_target(name, attribute.redefines, where)
            bindings[name] = _Binding(attribute, local_parts, where)
    return bindings


def _single_target(name: str, targets: tuple[str, ...], where: str) -> None:
    if len(targets) > 1:
        listed = ", ".join(targets)
        raise ValueError(
            f"usage '{name}' in {where} redefines more than one feature "
            f"({listed}); bind exactly one variation point."
        )


def derived_selection(
    architecture: Architecture, analysis: PartDefinition | str
) -> dict[str, str]:
    """The selection an analysis's configuration derives.

    Keys are relative to the composed model (``path``, ``path.inner_stage``) or
    bare for an analysis-local usage (``scenario``). Raises ``ValueError`` when a
    binding does not name a variation point or a point stays unselected.
    """
    definition = _definition(architecture, analysis)
    composed = model_usage(architecture, definition)[1]
    chain = _specialization_chain(architecture, composed)
    where = f"configuration '{composed.name}'"
    selection: dict[str, str] = {}

    bindings: dict[str, _Binding] = {}
    for configuration in chain[1:]:
        label = f"configuration '{configuration.name}'"
        bindings.update(_bindings(configuration, configuration.parts, label))
    _apply(architecture, chain[0], bindings, selection, "", where)

    for name, point in _points(architecture, definition).items():
        usage = definition.parts.get(name) or definition.attributes[name]
        binding = _Binding(usage, definition.parts, f"analysis '{definition.name}'")
        _select(architecture, point, binding, name, selection)
    return selection


def _apply(
    architecture: Architecture,
    scope: PartDefinition,
    bindings: Mapping[str, _Binding],
    selection: dict[str, str],
    prefix: str,
    where: str,
) -> None:
    """Bind *scope*'s points and require every one of them to be selected."""
    points = _points(architecture, scope)
    for target, binding in bindings.items():
        point = points.get(target)
        if point is None:
            raise ValueError(
                f"redefinition target '{target}' in {where} is not a variation "
                f"point in '{scope.name}'"
            )
        _select(architecture, point, binding, prefix + target, selection)
    for name, point in points.items():
        key = prefix + name
        if key not in selection:
            raise ValueError(
                f"variation point '{point.variation}' at '{key}' is not "
                f"selected; bind it in {where}"
            )


def _select(
    architecture: Architecture,
    point: _Point,
    binding: _Binding,
    key: str,
    selection: dict[str, str],
) -> None:
    """Record one binding and descend into the selected variant's type."""
    usage = binding.usage
    if not usage.value:
        raise ValueError(
            f"variation point '{point.variation}' at '{key}' is not selected; "
            f"bind it in {binding.where}"
        )
    variant = _resolve(architecture, point, binding, key)
    for existing in [item for item in selection if item == key or item.startswith(key + ".")]:
        del selection[existing]
    selection[key] = variant[0].name

    variant_member, body = variant
    if point.kind != "part" or variant_member.type_name is None:
        return
    nested = architecture.part_definitions.get(_short(variant_member.type_name))
    if nested is None:
        return
    inner: dict[str, _Binding] = {}
    if body is not None:
        inner = _bindings(body, {**binding.local_parts, **body.parts}, binding.where)
    _apply(architecture, nested, inner, selection, key + ".", binding.where)


def _resolve(
    architecture: Architecture,
    point: _Point,
    binding: _Binding,
    key: str,
) -> tuple[VariantMember, VariantBody | None]:
    """The variant a binding value names and the body that configures it.

    A qualified ``Type::variant`` value may carry a body on the same usage. An
    unqualified value names a local usage whose subsetting target is the variant
    and whose body binds the points inside that variant's type.
    """
    value = binding.usage.value
    assert value is not None
    if "::" in value:
        type_name, variant_name = (_short(part) for part in value.rsplit("::", 1))
        if type_name != point.variation:
            raise ValueError(
                f"binding '{value}' for variation point '{point.variation}' at "
                f"'{key}' names type '{type_name}'; expected '{point.variation}'"
            )
        return (
            _variant(point, variant_name, key, binding.where),
            getattr(binding.usage, "body", None),
        )

    local = binding.local_parts.get(value)
    if local is None:
        raise ValueError(
            f"binding '{value}' for variation point '{point.variation}' at "
            f"'{key}' names no part usage in {binding.where}"
        )
    if len(local.subsets) != 1:
        raise ValueError(
            f"part usage '{value}' in {binding.where} must specialise exactly "
            f"one variant of '{point.variation}'; found {len(local.subsets)}"
        )
    subset = local.subsets[0]
    type_name, variant_name = (_short(part) for part in subset.rsplit("::", 1))
    if type_name != point.variation:
        raise ValueError(
            f"part usage '{value}' in {binding.where} specialises '{subset}', "
            f"which is not a variant of '{point.variation}'"
        )
    return _variant(point, variant_name, key, binding.where), local.body


def _variant(
    point: _Point, name: str, key: str, where: str
) -> VariantMember:
    variant = next(
        (member for member in point.variants if member.name == name), None
    )
    if variant is None:
        expected = ", ".join(member.name for member in point.variants) or "none"
        raise ValueError(
            f"Unknown variant '{name}' for variation point '{point.variation}' "
            f"at '{key}' in {where}; expected one of {expected}."
        )
    return variant
