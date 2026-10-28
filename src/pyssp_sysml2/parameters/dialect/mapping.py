"""Expansion of applied parameter sets into SSP mapping entries and specs."""

from __future__ import annotations

import warnings

from pyssp_sysml2.core.control import is_control_attribute
from pyssp_sysml2.model import (
    Architecture,
    Attribute,
    AttributeDefinition,
    PartDefinition,
)
from pyssp_sysml2.parameters.dialect.composition import (
    AppliedSet,
    MappingSpec,
    applied_sets,
    set_usages,
)
from pyssp_sysml2.parameters.dialect.declarations import (
    fixed_count,
    parameter_interface,
)
from pyssp_sysml2.parameters.dialect.markers import (
    PARAMETER_SET_MARKER,
    is_parameter_set,
    validate_marker_definitions,
)


# -- mapping entries --------------------------------------------------------


def _expand_entries(
    source_name: str,
    target_name: str,
    source: Attribute,
    target: Attribute,
) -> list[tuple[str, str]]:
    """Source/target pairs for one mapped member, expanding fixed-length lists."""
    if source.value is None:
        raise ValueError(
            f"Parameter set member '{source_name}' has no value but is bound to "
            f"'{target_name}'"
        )
    if target.multiplicity:
        count = fixed_count(target.multiplicity, target_name)
        if not isinstance(source.value, tuple):
            raise ValueError(
                f"'{source_name}' must provide {count} values for list parameter "
                f"'{target_name}', got a scalar"
            )
        if len(source.value) != count:
            raise ValueError(
                f"'{source_name}' provides {len(source.value)} values but "
                f"'{target_name}' declares [{target.multiplicity}]"
            )
        return [
            (f"{source_name}[{index}]", f"{target_name}[{index}]")
            for index in range(count)
        ]
    if isinstance(source.value, tuple):
        raise ValueError(
            f"'{source_name}' is list-valued but target parameter '{target_name}' "
            "does not declare a multiplicity"
        )
    return [(source_name, target_name)]


def _member_type_error(
    source: Attribute, target: Attribute, source_name: str, target_name: str
) -> None:
    source_type = source.primitive_type_str()
    target_type = target.primitive_type_str()
    if source_type != target_type:
        raise ValueError(
            f"Parameter mapping '{source_name}' -> '{target_name}' has incompatible "
            f"types: {source_type} vs {target_type}"
        )


def _identity_entries(
    application: AppliedSet,
    interface: AttributeDefinition,
    component_name: str,
) -> list[tuple[str, str]]:
    """Expand a whole-object bind into identity mappings."""
    set_members = application.set_definition.attributes
    mapped: set[str] = set()
    entries: list[tuple[str, str]] = []
    for member_name, target in interface.attributes.items():
        if is_control_attribute(member_name):
            continue
        source = set_members.get(member_name)
        if source is None:
            continue
        _member_type_error(
            source, target, member_name, f"{component_name}.{member_name}"
        )
        entries.extend(
            _expand_entries(
                member_name,
                f"{component_name}.{member_name}",
                source,
                target,
            )
        )
        mapped.add(member_name)

    unmapped = [
        name
        for name, member in set_members.items()
        if member.value is not None and name not in mapped
    ]
    if unmapped:
        raise ValueError(
            f"Whole-object bind of '{application.usage_name}' to {component_name} "
            f"cannot map set members {', '.join(sorted(unmapped))}; use "
            "per-member binds for differently named parameters"
        )
    return entries


def mapping_entries(
    architecture: Architecture,
    system: PartDefinition,
    application: AppliedSet,
) -> list[tuple[str, str]]:
    """SSP ``(source, target)`` mapping entries for one applied set."""
    part_def = architecture.resolve_part(application.part_usage)
    if part_def is None:
        raise ValueError(
            f"Unresolved part definition for {application.component_name}"
        )
    interface = parameter_interface(architecture, part_def)
    if interface is None:
        raise ValueError(
            f"{part_def.name} declares no parameter interface, but "
            f"'{application.usage_name}' is bound to {application.component_name}"
        )

    component_name = application.component_name
    if application.identity:
        return _identity_entries(application, interface, component_name)

    set_members = application.set_definition.attributes
    entries: list[tuple[str, str]] = []
    bound_sources: set[str] = set()
    for bind in application.bindings:
        if (
            bind.port_path != application.component_path
            or bind.port_member is None
            or bind.set_member is None
        ):
            raise ValueError(
                "Per-member parameter binds must have the shape "
                "'<component>.parameters.<member> = <set>.<member>', got "
                f"'{'.'.join(bind.binding.source)} = "
                f"{'.'.join(bind.binding.target)}'"
            )
        source_name = bind.set_member
        target_name = bind.port_member
        source = set_members.get(source_name)
        if source is None:
            raise ValueError(
                f"Parameter set '{application.set_definition.name}' has no member "
                f"'{source_name}'"
            )
        target_attribute = interface.attributes.get(target_name)
        if target_attribute is None:
            raise ValueError(
                f"Parameter interface '{interface.name}' has no member '{target_name}'"
            )
        _member_type_error(source, target_attribute, source_name, target_name)
        entries.extend(
            _expand_entries(
                source_name,
                f"{component_name}.{target_name}",
                source,
                target_attribute,
            )
        )
        bound_sources.add(source_name)

    unused = sorted(
        name
        for name, member in set_members.items()
        if member.value is not None and name not in bound_sources
    )
    if unused:
        warnings.warn(
            f"Parameter set '{application.set_definition.name}' members "
            f"{', '.join(unused)} are not bound to {component_name}; "
            "SSP will ignore them",
            UserWarning,
            stacklevel=2,
        )
    return entries



# -- spec assembly ----------------------------------------------------------


def _validate_disjoint_targets(
    applications: list[tuple[AppliedSet, tuple[tuple[str, str], ...]]],
) -> None:
    """Reject two sets that bind the same component member.

    Multiple sets on one component are allowed only when their target members
    are disjoint. SysML ``bind`` has equality semantics, not an override order,
    so overlapping targets would be ambiguous when mapped to SSP.
    """
    by_component: dict[str, list[tuple[str, set[str]]]] = {}
    for application, entries in applications:
        component_name = application.component_name
        prefix = component_name + "."
        members: set[str] = set()
        for _source_name, target_name in entries:
            if not target_name.startswith(prefix):
                raise ValueError(
                    f"Parameter target '{target_name}' is outside component "
                    f"'{component_name}'"
                )
            members.add(target_name[len(prefix) :].split("[", 1)[0])
        by_component.setdefault(component_name, []).append(
            (application.usage_name, members)
        )

    for component_name, component_applications in by_component.items():
        seen: dict[str, str] = {}
        for usage_name, members in component_applications:
            for member_name in members:
                previous = seen.get(member_name)
                if previous is not None:
                    if previous == usage_name:
                        continue
                    raise ValueError(
                        f"Multiple parameter sets bind "
                        f"'{component_name}.{member_name}': {previous}, "
                        f"{usage_name}. Use disjoint target members."
                    )
                seen[member_name] = usage_name


def validate_applied_sets(
    architecture: Architecture, system: PartDefinition
) -> None:
    """Resolve every applied set's mapping and reject overlapping targets."""
    mapping_specs(architecture, system)


def _warn_unapplied_set_usages(
    architecture: Architecture,
    system: PartDefinition,
    applications: list[tuple[AppliedSet, tuple[tuple[str, str], ...]]],
) -> None:
    """Report set usages declared in the composition but bound to nothing."""
    applied_usages = {application.usage_name for application, _ in applications}
    for usage_name, usage in sorted(set_usages(architecture, system).items()):
        if usage_name in applied_usages:
            continue
        definition = architecture.resolve_attribute_def(usage)
        type_name = definition.name if definition is not None else usage.type_name
        warnings.warn(
            f"Parameter set '{usage_name}' ({type_name}) is declared but not "
            f"applied to any component of '{system.name}'; no parameter "
            "bindings or mappings are generated for it",
            UserWarning,
            stacklevel=3,
        )


def mapping_specs(
    architecture: Architecture, system: PartDefinition
) -> list[MappingSpec]:
    """Mapping entries for every applied set in a composition.

    A set usage declared in the composition but not bound to any component
    contributes no entries and is reported with a ``UserWarning``, naming it.
    """
    validate_marker_definitions(architecture)
    applications = [
        (
            application,
            tuple(mapping_entries(architecture, system, application)),
        )
        for application in applied_sets(architecture, system)
    ]
    _warn_unapplied_set_usages(architecture, system, applications)
    _validate_disjoint_targets(applications)
    specs = [
        MappingSpec(
            set_name=application.set_definition.name,
            set_usage=application.usage_name,
            component_path=application.component_path,
            identity=application.identity,
            entries=entries,
        )
        for application, entries in applications
    ]
    return sorted(
        specs, key=lambda spec: (spec.component_path, spec.set_name)
    )


# -- generation helpers -----------------------------------------------------


def parameter_sets_for_generation(
    architecture: Architecture,
    system: PartDefinition,
    *,
    set_names: list[str] | None = None,
    all_sets: bool = False,
) -> list[AttributeDefinition]:
    """Resolve the set definitions to emit, in deterministic name order."""
    if set_names:
        definitions: list[AttributeDefinition] = []
        for name in set_names:
            definition = architecture.attribute_definitions.get(name)
            if definition is None:
                raise ValueError(f"Unknown parameter set '{name}'")
            if not is_parameter_set(definition):
                raise ValueError(
                    f"'{name}' is not marked ':> {PARAMETER_SET_MARKER}'"
                )
            definitions.append(definition)
        return sorted(definitions, key=lambda item: item.name)

    if all_sets:
        return sorted(
            (
                definition
                for definition in architecture.attribute_definitions.values()
                if is_parameter_set(definition)
            ),
            key=lambda item: item.name,
        )

    definitions = {
        application.set_definition.name: application.set_definition
        for application in applied_sets(architecture, system)
    }
    return sorted(definitions.values(), key=lambda item: item.name)
