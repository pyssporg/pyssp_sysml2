"""Build and reconcile the component parameter interfaces.

A component with parameter connectors gets one parameter port typed by a
synthesized ``port def``; members are reconciled against the connectors
without disturbing unchanged defaults.
"""

from __future__ import annotations

from pyssp_standard import Component, System

from pyssp_sysml2.core.control import is_control_attribute
from pyssp_sysml2.metadata.fmu_metadata import is_fmu_metadata_definition
from pyssp_sysml2.model import (
    Architecture,
    Attribute,
    AttributeDefinition,
    PartDefinition,
    PortDefinition,
    PortUsage,
)
from pyssp_sysml2.parameters.dialect.markers import (
    PARAMETER_INTERFACE_MARKER,
    PARAMETER_SET_MARKER,
    PARAMETERS_PORT_NAME,
    is_parameter_interface,
)

from .inputs import (
    RESERVED_IDENTIFIERS,
    _identifier,
    _ssp_type_name,
    split_indexed,
)


# -- component parameter surfaces ------------------------------------------


def component_parameter_attributes(
    component: Component | System,
) -> list[Attribute]:
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
    interface: AttributeDefinition | PortDefinition, attributes: list[Attribute]
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
    while (
        candidate in architecture.attribute_definitions
        or candidate in architecture.port_definitions
    ):
        candidate = f"{base}_{counter}"
        counter += 1
    return candidate


def ensure_component_interface(
    architecture: Architecture,
    part_def: PartDefinition,
    component: Component | System,
    *,
    source_file: str,
) -> PortDefinition | None:
    """Create/update the component interface and its ``parameters`` port."""
    attributes = component_parameter_attributes(component)
    if not attributes:
        return None

    if PARAMETERS_PORT_NAME in part_def.attributes:
        raise ValueError(
            f"{part_def.name}.{PARAMETERS_PORT_NAME} is an attribute bag; parameter "
            "interfaces are port defs. Use "
            f"'in port {PARAMETERS_PORT_NAME} : <PortDef>;' instead."
        )

    port_usage = part_def.ports.get(PARAMETERS_PORT_NAME)
    if port_usage is not None:
        interface = architecture.resolve_port(port_usage)
        if interface is None:
            raise ValueError(
                f"{part_def.name}.parameters is not typed by a port definition"
            )
        if not is_parameter_interface(interface):
            raise ValueError(
                f"Parameter port {part_def.name}.parameters is typed by "
                f"'{interface.name}', which is not marked ':> {PARAMETER_INTERFACE_MARKER}'"
            )
        if port_usage.direction not in (None, "in"):
            raise ValueError(
                f"Parameter port {part_def.name}.parameters must be "
                f"undirected or 'in', got '{port_usage.direction}'"
            )
        _reconcile_interface(interface, attributes)
        return interface

    flat = [
        name
        for name, attribute in part_def.attributes.items()
        if not is_control_attribute(name)
        and not is_fmu_metadata_definition(
            architecture, architecture.resolve_attribute_def(attribute)
        )
    ]
    if flat:
        raise ValueError(
            f"{part_def.name} mixes flat parameter attributes "
            f"({', '.join(sorted(flat))}) with a synthesized parameter interface"
        )
    if PARAMETERS_PORT_NAME in part_def.parts:
        raise ValueError(
            f"{part_def.name} already has a subpart named "
            f"'{PARAMETERS_PORT_NAME}'"
        )

    interface_name = _interface_name(architecture, part_def)
    interface = PortDefinition(
        name=interface_name,
        source_file=source_file,
        specializes=(PARAMETER_INTERFACE_MARKER,),
    )
    interface.attributes.update({attribute.name: attribute for attribute in attributes})
    architecture.add_port_def(interface)
    part_def.ports[PARAMETERS_PORT_NAME] = PortUsage(
        name=PARAMETERS_PORT_NAME,
        direction="in",
        type_name=interface_name,
    )
    return interface


def ensure_marker_definitions(architecture: Architecture, source_file: str) -> None:
    if PARAMETER_INTERFACE_MARKER not in architecture.port_definitions:
        architecture.add_port_def(
            PortDefinition(name=PARAMETER_INTERFACE_MARKER, source_file=source_file)
        )
    if PARAMETER_SET_MARKER not in architecture.attribute_definitions:
        architecture.add_attribute_def(
            AttributeDefinition(name=PARAMETER_SET_MARKER, source_file=source_file)
        )
