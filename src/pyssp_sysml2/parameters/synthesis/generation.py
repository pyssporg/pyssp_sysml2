"""Synthesize the SysML parameter dialect from SSD connectors and bindings.

The SSD is the source of truth here:

- ``kind="parameter"`` connectors define a component's parameter interface;
- ``ssd:ParameterBinding`` entries (system or component level) point at an
  SSV and optionally carry an inline or external SSM mapping.

This module turns that into ``port def ... :> ParameterInterface`` and
``attribute def ... :> ParameterSet`` definitions, an ``in port parameters``
on each component part definition, composition set usages, and explicit
``bind`` statements.

Nested SSD systems become nested part paths (``outer.inner``). Several sets
may be applied to one parameterable element as long as their target members
are disjoint; overlapping targets are rejected because SysML ``bind`` is an
equality constraint, not an override.
"""

from __future__ import annotations

from pathlib import Path

from pyssp_sysml2.core.control import is_control_attribute
from pyssp_sysml2.model import (
    Architecture,
    Attribute,
    AttributeDefinition,
    Binding,
    PartDefinition,
    PartUsage,
    PortDefinition,
)
from pyssp_sysml2.parameters.dialect.composition import validate_parameter_dialect
from pyssp_sysml2.parameters.dialect.mapping import validate_applied_sets
from pyssp_sysml2.parameters.dialect.markers import (
    PARAMETER_SET_MARKER,
    PARAMETERS_PORT_NAME,
    is_parameter_set,
    validate_marker_definitions,
)

from .application import (
    _absolute_values,
    _applications_for_binding,
    _normalize_values,
)
from .inputs import (
    SetApplication,
    SetBuild,
    _all_bindings,
    _binding_parameters,
    _component_map,
    _group_values,
    _identifier,
)
from .interfaces import ensure_component_interface, ensure_marker_definitions


# -- public synthesis -------------------------------------------------------


def _set_from_values(
    name: str,
    values: dict[str, tuple[str, object]],
    *,
    source_file: str,
) -> AttributeDefinition:
    definition = AttributeDefinition(
        name=name,
        source_file=source_file,
        specializes=(PARAMETER_SET_MARKER,),
    )
    for base in sorted(values):
        type_name, value = values[base]
        definition.attributes[base] = Attribute(
            name=base,
            type_name=type_name,
            value=value,
            multiplicity=str(len(value)) if isinstance(value, tuple) else None,
        )
    return definition


def _signature(definition: AttributeDefinition) -> tuple:
    return tuple(
        sorted(
            (
                attribute.name,
                attribute.effective_type_name,
                attribute.multiplicity,
                attribute.value,
            )
            for attribute in definition.attributes.values()
        )
    )


def _unique_name(base: str, used: set[str]) -> str:
    candidate = base
    counter = 2
    while candidate in used:
        candidate = f"{base}_{counter}"
        counter += 1
    used.add(candidate)
    return candidate


def _remove_parameter_usage(
    architecture: Architecture, system: PartDefinition
) -> None:
    system.bindings = [
        binding
        for binding in system.bindings
        if PARAMETERS_PORT_NAME not in binding.source
        and PARAMETERS_PORT_NAME not in binding.target
    ]
    for name, attribute in list(system.attributes.items()):
        if is_control_attribute(name):
            continue
        if is_parameter_set(architecture.resolve_attribute_def(attribute)):
            del system.attributes[name]


def _part_at_path(
    architecture: Architecture,
    system: PartDefinition,
    path: tuple[str, ...],
):
    """Resolve a nested part usage path to its usage and definition."""
    current = system
    usage: PartUsage | None = None
    for name in path:
        usage = current.parts.get(name)
        if usage is None:
            return None, None
        current = architecture.resolve_part(usage)
        if current is None:
            return usage, None
    return usage, current


def synthesize_parameter_dialect(
    architecture: Architecture,
    system: PartDefinition,
    ssd_system,
    ssd_path: Path | None = None,
    *,
    source_file: str = "architecture.sysml",
    sync: bool = False,
) -> None:
    """Build the parameter dialect from SSD connectors and parameter bindings."""
    components = _component_map(ssd_system)
    if not components:
        return
    if any(
        connector.kind == "parameter"
        for connector in ssd_system.connectors
    ):
        raise ValueError(
            "Top-level SSD system parameter connectors are not supported; "
            "attach parameter connectors to component or nested-system elements"
        )

    bindings = _all_bindings(ssd_system)
    has_parameter_surface = bool(bindings) or any(
        connector.kind == "parameter"
        for component in components.values()
        for connector in component.connectors
    )
    if not has_parameter_surface:
        if sync:
            _remove_parameter_usage(architecture, system)
            for component_path in components:
                _, part_def = _part_at_path(
                    architecture, system, component_path
                )
                if part_def is not None:
                    part_def.ports.pop(PARAMETERS_PORT_NAME, None)
        return

    ensure_marker_definitions(architecture, source_file)

    interfaces: dict[tuple[str, ...], PortDefinition | None] = {}
    for component_path in sorted(components):
        part_usage, part_def = _part_at_path(
            architecture, system, component_path
        )
        if part_usage is None or part_def is None:
            continue
        interface = ensure_component_interface(
            architecture,
            part_def,
            components[component_path],
            source_file=source_file,
        )
        interfaces[component_path] = interface
        if interface is None and sync:
            part_def.ports.pop(PARAMETERS_PORT_NAME, None)

    if sync:
        _remove_parameter_usage(architecture, system)

    set_builds: dict[str, SetBuild] = {}
    used_set_names = set(architecture.attribute_definitions)

    def add_set(
        requested_name: str,
        values: dict[str, tuple[str, object]],
        application: SetApplication,
        component: str,
    ) -> None:
        if not values:
            raise ValueError(f"Parameter set '{requested_name}' has no values")
        base_name = _identifier(requested_name, f"{component}ParameterSet")
        candidate = base_name
        definition = _set_from_values(candidate, values, source_file=source_file)
        signature = _signature(definition)

        while True:
            build = set_builds.get(candidate)
            if build is not None:
                if _signature(build.definition) == signature:
                    build.applications.append(application)
                    return
                candidate = _unique_name(
                    f"{base_name}_{_identifier(component, 'set')}", used_set_names
                )
                definition = _set_from_values(candidate, values, source_file=source_file)
                signature = _signature(definition)
                continue

            existing = architecture.attribute_definitions.get(candidate)
            if existing is not None:
                if is_parameter_set(existing) and (
                    sync or _signature(existing) == signature
                ):
                    if sync:
                        existing.attributes.clear()
                        existing.attributes.update(definition.attributes)
                    set_builds[candidate] = SetBuild(existing, [application])
                    return
                candidate = _unique_name(
                    f"{base_name}_{_identifier(component, 'set')}", used_set_names
                )
                definition = _set_from_values(candidate, values, source_file=source_file)
                signature = _signature(definition)
                continue

            architecture.add_attribute_def(definition)
            used_set_names.add(candidate)
            set_builds[candidate] = SetBuild(definition, [application])
            return

    for owner_path, component_level, binding in bindings:
        set_name, parameters = _binding_parameters(binding, ssd_path)
        values = _group_values(parameters)
        application_values = (
            values
            if binding.prefix
            else _absolute_values(values, owner_path)
        )
        applications = _applications_for_binding(
            owner_path,
            component_level,
            binding,
            application_values,
            set(components),
            interfaces,
            ssd_path,
        )
        for application in applications:
            normalized = _normalize_values(
                application_values, application.component_path
            )
            add_set(
                set_name, normalized, application, application.component_name
            )

    if not set_builds:
        return

    for set_name in sorted(set_builds):
        build = set_builds[set_name]
        usage_base = (
            f"{set_name}_set" if set_name == PARAMETERS_PORT_NAME else set_name
        )
        usage_name = _unique_name(
            usage_base, set(system.attributes) | set(system.parts)
        )
        system.attributes[usage_name] = Attribute(
            name=usage_name, type_name=build.definition.name
        )
        for application in build.applications:
            if application.identity:
                bindings = [
                    Binding(
                        source=application.component_path
                        + (PARAMETERS_PORT_NAME,),
                        target=(usage_name,),
                    )
                ]
            else:
                bindings = [
                    Binding(
                        source=application.component_path
                        + (PARAMETERS_PORT_NAME, pair.target),
                        target=(usage_name, pair.source),
                    )
                    for pair in application.pairs
                ]
            for binding in bindings:
                if all(existing.key != binding.key for existing in system.bindings):
                    system.bindings.append(binding)

    validate_marker_definitions(architecture)
    validate_parameter_dialect(architecture, system)
    validate_applied_sets(architecture, system)
