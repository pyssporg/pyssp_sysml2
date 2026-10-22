"""Synthesize the SysML parameter dialect from SSD connectors and bindings.

The SSD is the source of truth here:

- ``kind="parameter"`` connectors define a component's parameter interface;
- ``ssd:ParameterBinding`` entries (system or component level) point at an
  SSV and optionally carry an inline or external SSM mapping.

This module turns that into ``attribute def ... :> ParameterInterface`` /
``:> ParameterSet`` definitions, a ``parameters`` bag on each component part
definition, composition set usages, and explicit ``bind`` statements.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pyssp_standard.ssd import Component
from pyssp_standard.ssm import SSM
from pyssp_standard.ssv import SSV

from pyssp_sysml2.control import (
    CONTROL_PREFIX,
    PARAMETER_SET_ATTR,
    is_control_attribute,
)
from pyssp_sysml2.parameters import (
    PARAMETERS_BAG_NAME,
    PARAMETER_INTERFACE_MARKER,
    PARAMETER_SET_MARKER,
    coerce_parameter_value,
    fixed_count,
    is_parameter_interface,
    is_parameter_set,
    validate_applied_sets,
    validate_marker_definitions,
    validate_parameter_dialect,
)
from pyssp_sysml2.sysml_model import (
    Architecture,
    Attribute,
    AttributeDefinition,
    Binding,
    PartDefinition,
)

SSP_TYPES = {"Real", "Integer", "Boolean", "String"}

# SysML keywords that cannot be used as feature/definition names by sysmlpy.
# Parameter names using one of these are rejected rather than emitting a file
# that the loader cannot read back.
RESERVED_IDENTIFIERS = {
    "action",
    "alias",
    "allocate",
    "analysis",
    "attribute",
    "bind",
    "calc",
    "comment",
    "concern",
    "connection",
    "constraint",
    "def",
    "dependency",
    "doc",
    "expose",
    "flow",
    "import",
    "interface",
    "item",
    "metadata",
    "occurrence",
    "package",
    "part",
    "perform",
    "port",
    "ref",
    "rendering",
    "requirement",
    "satisfy",
    "stakeholder",
    "state",
    "typed",
    "verification",
    "view",
    "viewpoint",
}


@dataclass(frozen=True)
class MappingPair:
    component: str
    source: str
    target: str
    count: int | None = None


@dataclass(frozen=True)
class SetApplication:
    component: str
    identity: bool
    pairs: tuple[MappingPair, ...]


@dataclass
class SetBuild:
    definition: AttributeDefinition
    applications: list[SetApplication]


# -- small parsing helpers --------------------------------------------------


def _identifier(name: str, fallback: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_]", "_", name).strip("_")
    if not cleaned:
        cleaned = fallback
    if cleaned in RESERVED_IDENTIFIERS:
        cleaned = f"p_{cleaned}"
    if cleaned[0].isdigit():
        cleaned = f"_{cleaned}"
    return cleaned


def split_indexed(name: str) -> tuple[str, int | None]:
    """Split ``x[2]`` into ``("x", 2)``; leave scalar names alone."""
    if not name:
        raise ValueError("Parameter name must not be empty")
    if name.endswith("]") and "[" in name:
        base, _, raw_index = name.rpartition("[")
        try:
            index = int(raw_index[:-1])
        except ValueError:
            raise ValueError(f"Unsupported parameter index in '{name}'") from None
        if index < 0:
            raise ValueError(f"Unsupported negative parameter index in '{name}'")
        return base, index
    return name, None


def _ssp_type_name(type_name: str | None) -> str:
    if type_name == "Enumeration":
        return "Integer"
    if type_name in SSP_TYPES:
        return type_name
    return "Real"


def _group_values(
    parameters: Iterable[tuple[str, str | None, object]],
) -> dict[str, tuple[str, object]]:
    """Group SSV parameters into base names with scalar or tuple values."""
    grouped: dict[str, dict[int | None, tuple[str, object]]] = {}
    for name, raw_type, raw_value in parameters:
        base, index = split_indexed(name)
        if not base:
            raise ValueError(f"Parameter '{name}' has an empty base name")
        if is_control_attribute(base):
            raise ValueError(
                f"Parameter '{name}' uses the reserved '{CONTROL_PREFIX}' prefix"
            )
        if base in RESERVED_IDENTIFIERS:
            raise ValueError(
                f"Parameter '{name}' uses reserved SysML keyword '{base}'"
            )
        type_name = _ssp_type_name(raw_type)
        if raw_value is None:
            raise ValueError(f"Parameter '{name}' has no value in the parameter set")
        value = coerce_parameter_value(type_name, raw_value)
        grouped.setdefault(base, {})[index] = (type_name, value)

    result: dict[str, tuple[str, object]] = {}
    for base, by_index in grouped.items():
        if None in by_index:
            if len(by_index) > 1:
                raise ValueError(
                    f"Parameter '{base}' mixes scalar and indexed values"
                )
            result[base] = by_index[None]
            continue
        indices = sorted(index for index in by_index if index is not None)
        if indices != list(range(len(indices))):
            raise ValueError(
                f"Parameter '{base}' has non-contiguous indices {indices}"
            )
        types = {by_index[index][0] for index in indices}
        if len(types) > 1:
            raise ValueError(
                f"Parameter '{base}' mixes types {', '.join(sorted(types))}"
            )
        result[base] = (
            types.pop(),
            tuple(by_index[index][1] for index in indices),
        )
    return result


def _ssv_parameters(parameter_set) -> list[tuple[str, str | None, object]]:
    return [
        (parameter.name, parameter.type_name, parameter.attributes.get("value"))
        for parameter in parameter_set.parameters
    ]


def _resolve_relative(ssd_path: Path | None, source: str) -> Path:
    if ssd_path is None:
        raise ValueError(
            f"Parameter set source '{source}' cannot be resolved without the SSD path"
        )
    path = (ssd_path.parent / source).resolve()
    if not path.is_file():
        raise ValueError(f"Parameter set source not found: {source}")
    return path


def _binding_parameters(
    binding, ssd_path: Path | None
) -> tuple[str, list[tuple[str, str | None, object]]]:
    if binding.parameter_set is not None:
        return (
            binding.parameter_set.name,
            _ssv_parameters(binding.parameter_set),
        )
    if binding.source is None:
        raise ValueError("ParameterBinding has neither inline values nor a source")
    path = _resolve_relative(ssd_path, binding.source)
    with SSV(path, mode="r") as ssv:
        return ssv.xml.name, _ssv_parameters(ssv.xml)


def _mapping_entries(mapping_document) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for mapping in mapping_document.mappings:
        if mapping.transformation is not None:
            raise ValueError("SSM transformations are not supported")
        if mapping.suppress_unit_conversion:
            raise ValueError("SSM unit-conversion suppression is not supported")
        entries.append((mapping.source, mapping.target))
    return entries


def _binding_mapping(
    binding, ssd_path: Path | None
) -> list[tuple[str, str]] | None:
    parameter_mapping = binding.parameter_mapping
    if parameter_mapping is None:
        return None
    if parameter_mapping.mapping is not None:
        return _mapping_entries(parameter_mapping.mapping)
    if parameter_mapping.source is None:
        raise ValueError("ParameterBinding mapping has neither inline mapping nor a source")
    path = _resolve_relative(ssd_path, parameter_mapping.source)
    with SSM(path, mode="r") as ssm:
        return _mapping_entries(ssm.xml)


def _all_bindings(ssd_system) -> list[tuple[str | None, object]]:
    bindings: list[tuple[str | None, object]] = [
        (None, binding) for binding in ssd_system.parameter_bindings
    ]
    for element in ssd_system.elements:
        if isinstance(element, Component):
            bindings.extend(
                (element.name, binding) for binding in element.parameter_bindings
            )
    return bindings


# -- component parameter surfaces ------------------------------------------


def component_parameter_attributes(component: Component) -> list[Attribute]:
    """Interface members implied by a component's parameter connectors."""
    grouped: dict[str, dict[int | None, str]] = {}
    for connector in component.connectors:
        if connector.kind != "parameter":
            continue
        base, index = split_indexed(connector.name)
        if (
            not base
            or "." in base
            or is_control_attribute(base)
            or base in RESERVED_IDENTIFIERS
        ):
            raise ValueError(
                f"Parameter connector '{connector.name}' cannot be represented "
                "as a SysML attribute name"
            )
        grouped.setdefault(base, {})[index] = _ssp_type_name(connector.type_name)

    attributes: list[Attribute] = []
    for base in sorted(grouped):
        by_index = grouped[base]
        if None in by_index:
            if len(by_index) > 1:
                raise ValueError(
                    f"Parameter '{base}' mixes scalar and indexed connectors"
                )
            attributes.append(Attribute(name=base, type_name=by_index[None]))
            continue
        indices = sorted(index for index in by_index if index is not None)
        if indices != list(range(len(indices))):
            raise ValueError(
                f"Parameter '{base}' has non-contiguous connector indices {indices}"
            )
        types = {by_index[index] for index in indices}
        if len(types) > 1:
            raise ValueError(
                f"Parameter '{base}' mixes types {', '.join(sorted(types))}"
            )
        attributes.append(
            Attribute(
                name=base,
                type_name=types.pop(),
                multiplicity=str(len(indices)),
            )
        )
    return attributes


def _reconcile_interface(
    interface: AttributeDefinition, attributes: list[Attribute]
) -> None:
    """Replace interface members, keeping defaults for unchanged signatures."""
    existing = interface.attributes
    updated: dict[str, Attribute] = {}
    for attribute in attributes:
        previous = existing.get(attribute.name)
        if (
            previous is not None
            and previous.effective_type_name == attribute.effective_type_name
            and previous.multiplicity == attribute.multiplicity
        ):
            attribute.value = previous.value
            attribute.doc = previous.doc
        updated[attribute.name] = attribute
    interface.attributes.clear()
    interface.attributes.update(updated)


def _interface_name(
    architecture: Architecture, part_def: PartDefinition
) -> str:
    base = _identifier(f"{part_def.name}Parameters", "Parameters")
    candidate = base
    counter = 2
    while candidate in architecture.attribute_definitions:
        candidate = f"{base}_{counter}"
        counter += 1
    return candidate


def ensure_component_interface(
    architecture: Architecture,
    part_def: PartDefinition,
    component: Component,
    *,
    source_file: str,
) -> AttributeDefinition | None:
    """Create/update the component interface and its ``parameters`` bag."""
    attributes = component_parameter_attributes(component)
    if not attributes:
        return None

    bag = part_def.attributes.get(PARAMETERS_BAG_NAME)
    if bag is not None:
        interface = architecture.resolve_attribute_def(bag)
        if interface is None:
            raise ValueError(
                f"{part_def.name}.parameters is not typed by an attribute definition"
            )
        if not is_parameter_interface(interface):
            raise ValueError(
                f"Parameter bag {part_def.name}.parameters is typed by "
                f"'{interface.name}', which is not marked ':> {PARAMETER_INTERFACE_MARKER}'"
            )
        _reconcile_interface(interface, attributes)
        return interface

    flat = [
        name
        for name in part_def.attributes
        if name != PARAMETERS_BAG_NAME and not is_control_attribute(name)
    ]
    if flat:
        raise ValueError(
            f"{part_def.name} mixes flat parameter attributes "
            f"({', '.join(sorted(flat))}) with a synthesized parameter interface"
        )
    if PARAMETERS_BAG_NAME in part_def.ports or PARAMETERS_BAG_NAME in part_def.parts:
        raise ValueError(
            f"{part_def.name} already has a port or subpart named "
            f"'{PARAMETERS_BAG_NAME}'"
        )

    interface_name = _interface_name(architecture, part_def)
    interface = AttributeDefinition(
        name=interface_name,
        source_file=source_file,
        specializes=(PARAMETER_INTERFACE_MARKER,),
    )
    interface.attributes.update({attribute.name: attribute for attribute in attributes})
    architecture.add_attribute_def(interface)
    part_def.attributes[PARAMETERS_BAG_NAME] = Attribute(
        name=PARAMETERS_BAG_NAME, type_name=interface_name
    )
    return interface


def ensure_marker_definitions(architecture: Architecture, source_file: str) -> None:
    for marker in (PARAMETER_INTERFACE_MARKER, PARAMETER_SET_MARKER):
        if marker not in architecture.attribute_definitions:
            architecture.add_attribute_def(
                AttributeDefinition(name=marker, source_file=source_file)
            )


# -- bindings to sets -------------------------------------------------------


def _mapping_pairs(
    entries: Iterable[tuple[str, str]], components: set[str]
) -> list[MappingPair]:
    grouped: dict[tuple[str, str, str], dict[int | None, int | None]] = {}
    for source, target in entries:
        target_base, target_index = split_indexed(target)
        parts = target_base.split(".")
        if len(parts) != 2:
            raise ValueError(
                f"Parameter mapping target '{target}' must be '<component>.<parameter>'"
            )
        component, target_member = parts
        if (
            not component
            or not target_member
            or target_member in RESERVED_IDENTIFIERS
        ):
            raise ValueError(
                f"Parameter mapping target '{target}' must be '<component>.<parameter>'"
            )
        if component not in components:
            raise ValueError(
                f"Parameter mapping target '{target}' references unknown component "
                f"'{component}'"
            )
        source_base, source_index = split_indexed(source)
        if source_base.startswith(f"{component}."):
            source_base = source_base[len(component) + 1 :]
        if "." in source_base or source_base in RESERVED_IDENTIFIERS:
            raise ValueError(
                f"Parameter mapping source '{source}' cannot be represented as a "
                "SysML attribute name"
            )
        if (source_index is None) != (target_index is None):
            raise ValueError(
                f"Parameter mapping '{source}' -> '{target}' must use indices on "
                "both sides or on neither side"
            )
        key = (component, source_base, target_member)
        grouped.setdefault(key, {})[source_index] = target_index

    pairs: list[MappingPair] = []
    seen_sources: set[tuple[str, str]] = set()
    seen_targets: set[tuple[str, str]] = set()
    for (component, source_base, target_member), indices in grouped.items():
        count: int | None = None
        if None in indices:
            if len(indices) > 1:
                raise ValueError(
                    f"Mapping for '{source_base}' mixes scalar and indexed entries"
                )
        else:
            source_indices = sorted(index for index in indices if index is not None)
            target_indices = sorted(
                index for index in indices.values() if index is not None
            )
            if source_indices != target_indices:
                raise ValueError(
                    f"Mapping for '{source_base}' must map matching indices, got "
                    f"{source_indices} -> {target_indices}"
                )
            if source_indices != list(range(len(source_indices))):
                raise ValueError(
                    f"Mapping for '{source_base}' has non-contiguous indices "
                    f"{source_indices}"
                )
            count = len(source_indices)
        source_key = (component, source_base)
        target_key = (component, target_member)
        if source_key in seen_sources:
            raise ValueError(
                f"Parameter source '{source_base}' maps to more than one target "
                f"for component '{component}'"
            )
        if target_key in seen_targets:
            raise ValueError(
                f"Parameter target '{target_member}' is mapped more than once for "
                f"component '{component}'"
            )
        seen_sources.add(source_key)
        seen_targets.add(target_key)
        pairs.append(MappingPair(component, source_base, target_member, count))
    return sorted(pairs, key=lambda pair: (pair.component, pair.source, pair.target))


def _normalize_values(
    values: dict[str, tuple[str, object]], component: str
) -> dict[str, tuple[str, object]]:
    normalized: dict[str, tuple[str, object]] = {}
    for base, item in values.items():
        if base.startswith(f"{component}."):
            base = base[len(component) + 1 :]
        if not base or "." in base or base in RESERVED_IDENTIFIERS:
            raise ValueError(
                f"Parameter '{base}' cannot be represented as a SysML attribute name"
            )
        normalized[base] = item
    return normalized


def _infer_component(
    values: dict[str, tuple[str, object]],
    components: set[str],
    interfaces: dict[str, AttributeDefinition | None],
) -> str:
    prefixes = {base.split(".", 1)[0] for base in values if "." in base}
    if len(prefixes) == 1:
        candidate = prefixes.pop()
        if candidate in components:
            return candidate

    matches = []
    for component in sorted(components):
        interface = interfaces.get(component)
        if interface is None:
            continue
        names = set(interface.attributes)
        normalized = {
            base[len(component) + 1 :] if base.startswith(f"{component}.") else base
            for base in values
        }
        if normalized <= names:
            matches.append(component)
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError(
            "Cannot infer which component a parameter set applies to; add a "
            "ParameterBinding prefix or ParameterMapping"
        )
    raise ValueError(
        "Parameter set application is ambiguous between components "
        f"{', '.join(matches)}; add a ParameterBinding prefix or ParameterMapping"
    )


def _check_pair_shape(
    pair: MappingPair,
    normalized: dict[str, tuple[str, object]],
    interfaces: dict[str, AttributeDefinition | None],
) -> None:
    _, source_value = normalized[pair.source]
    interface = interfaces.get(pair.component)
    if interface is None:
        raise ValueError(
            f"SSD applies a parameter set to '{pair.component}', but that "
            "component has no parameter connectors"
        )
    target = interface.attributes.get(pair.target)
    if target is None:
        raise ValueError(
            f"Parameter mapping target '{pair.target}' does not exist on "
            f"component '{pair.component}'"
        )
    if pair.count is None:
        if isinstance(source_value, tuple):
            raise ValueError(
                f"Mapping source '{pair.source}' is a list but the mapping has "
                "no indices"
            )
        if target.multiplicity:
            raise ValueError(
                f"Mapping target '{pair.target}' declares [{target.multiplicity}] "
                "but the mapping has no indices"
            )
        return

    if not isinstance(source_value, tuple) or len(source_value) != pair.count:
        raise ValueError(
            f"Mapping source '{pair.source}' must contain {pair.count} values"
        )
    if (
        not target.multiplicity
        or fixed_count(target.multiplicity, pair.target) != pair.count
    ):
        raise ValueError(
            f"Mapping target '{pair.target}' must declare [{pair.count}] to match "
            f"the {pair.count} mapped indices"
        )


def _applications_for_binding(
    owner: str | None,
    binding,
    values: dict[str, tuple[str, object]],
    components: set[str],
    interfaces: dict[str, AttributeDefinition | None],
    ssd_path: Path | None,
) -> list[SetApplication]:
    mapping = _binding_mapping(binding, ssd_path)
    if mapping is not None:
        pairs = _mapping_pairs(mapping, components)
        if not pairs:
            raise ValueError("ParameterBinding contains an empty ParameterMapping")
        by_component: dict[str, list[MappingPair]] = {}
        for pair in pairs:
            by_component.setdefault(pair.component, []).append(pair)
        if owner is not None and set(by_component) != {owner}:
            raise ValueError(
                f"Component-level parameter binding for '{owner}' maps to "
                f"components {', '.join(sorted(by_component))}"
            )
        if binding.prefix:
            prefix_component = binding.prefix.rstrip(".")
            if set(by_component) != {prefix_component}:
                raise ValueError(
                    f"ParameterBinding prefix '{binding.prefix}' conflicts with "
                    f"mapping targets {', '.join(sorted(by_component))}"
                )
        for pair in pairs:
            normalized = _normalize_values(values, pair.component)
            if pair.source not in normalized:
                raise ValueError(
                    f"Parameter mapping source '{pair.source}' is not present in "
                    "the parameter set"
                )
            _check_pair_shape(pair, normalized, interfaces)
        return [
            SetApplication(component, False, tuple(pairs))
            for component, pairs in sorted(by_component.items())
        ]

    if owner is not None:
        component = owner
        if binding.prefix and binding.prefix.rstrip(".") != owner:
            raise ValueError(
                f"Component-level parameter binding for '{owner}' has conflicting "
                f"prefix '{binding.prefix}'"
            )
    elif binding.prefix:
        component = binding.prefix.rstrip(".")
        if component not in components:
            raise ValueError(
                f"ParameterBinding prefix '{binding.prefix}' references unknown component"
            )
    else:
        component = _infer_component(values, components, interfaces)

    normalized = _normalize_values(values, component)
    interface = interfaces.get(component)
    if interface is None:
        raise ValueError(
            f"SSD applies a parameter set to '{component}', but that component "
            "has no parameter connectors"
        )
    missing = sorted(set(normalized) - set(interface.attributes))
    if missing:
        raise ValueError(
            f"Parameter set members {', '.join(missing)} do not exist on "
            f"component '{component}'"
        )
    return [SetApplication(component, True, ())]


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
        if not (
            len(binding.target) >= 2
            and binding.target[1] == PARAMETERS_BAG_NAME
        )
    ]
    for name, attribute in list(system.attributes.items()):
        if is_control_attribute(name):
            continue
        if is_parameter_set(architecture.resolve_attribute_def(attribute)):
            del system.attributes[name]
    system.attributes.pop(PARAMETER_SET_ATTR, None)


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
    components = {
        element.name: element
        for element in ssd_system.elements
        if isinstance(element, Component) and element.name
    }
    if not components:
        return

    bindings = _all_bindings(ssd_system)
    has_parameter_surface = bool(bindings) or any(
        connector.kind == "parameter"
        for component in components.values()
        for connector in component.connectors
    )
    if not has_parameter_surface:
        if sync:
            _remove_parameter_usage(architecture, system)
            for component_name in components:
                part_usage = system.parts.get(component_name)
                part_def = (
                    architecture.resolve_part(part_usage)
                    if part_usage is not None
                    else None
                )
                if part_def is not None:
                    part_def.attributes.pop(PARAMETERS_BAG_NAME, None)
        return

    ensure_marker_definitions(architecture, source_file)

    interfaces: dict[str, AttributeDefinition | None] = {}
    for component_name in sorted(components):
        part_usage = system.parts.get(component_name)
        if part_usage is None:
            continue
        part_def = architecture.resolve_part(part_usage)
        if part_def is None:
            continue
        interface = ensure_component_interface(
            architecture,
            part_def,
            components[component_name],
            source_file=source_file,
        )
        interfaces[component_name] = interface
        if interface is None and sync:
            part_def.attributes.pop(PARAMETERS_BAG_NAME, None)

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

    for owner, binding in bindings:
        set_name, parameters = _binding_parameters(binding, ssd_path)
        values = _group_values(parameters)
        applications = _applications_for_binding(
            owner, binding, values, set(components), interfaces, ssd_path
        )
        for application in applications:
            normalized = _normalize_values(values, application.component)
            add_set(set_name, normalized, application, application.component)

    if not set_builds:
        return

    for set_name in sorted(set_builds):
        build = set_builds[set_name]
        usage_base = (
            f"{set_name}_set" if set_name == PARAMETERS_BAG_NAME else set_name
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
                        source=(usage_name,),
                        target=(application.component, PARAMETERS_BAG_NAME),
                    )
                ]
            else:
                bindings = [
                    Binding(
                        source=(usage_name, pair.source),
                        target=(
                            application.component,
                            PARAMETERS_BAG_NAME,
                            pair.target,
                        ),
                    )
                    for pair in application.pairs
                ]
            for binding in bindings:
                if all(existing.key != binding.key for existing in system.bindings):
                    system.bindings.append(binding)

    validate_marker_definitions(architecture)
    validate_parameter_dialect(architecture, system)
    validate_applied_sets(architecture, system)
