"""Generic SSD generation helpers."""

from __future__ import annotations

from pathlib import Path

from pyssp_standard.ssd import (
    Component,
    Connection,
    Connector,
    DefaultExperiment,
    ParameterBinding,
    SSD,
    System,
)
from pyssp_standard.standard.ssp1.model import (
    Ssd1ParameterMappingReference,
    Ssp1ParameterMapping,
)

from pyssp_sysml2.control import PARAMETER_SET_ATTR, is_control_attribute
from pyssp_sysml2.fmi_helpers import fmu_resource_path, to_fmi_direction_definition
from pyssp_sysml2.parameters import (
    MappingSpec,
    has_parameter_dialect,
    mapping_specs,
    parameter_declarations,
    parameter_interface,
    parameter_items,
    validate_parameter_dialect,
)
from pyssp_sysml2.paths import ensure_parent_dir
from pyssp_sysml2.sysml import (
    DEFAULT_START_ATTR,
    DEFAULT_STOP_ATTR,
    FLAT_CONNECTOR_ATTR,
    IMPLEMENTATION_ATTR,
)
from pyssp_sysml2.sysml_model import Architecture, PartDefinition, load


def _endpoint_port_def(
    system: PartDefinition,
    architecture: Architecture,
    part_name: str,
    port_name: str,
):
    """Resolve a connection endpoint to its port definition."""
    part_usage = system.parts.get(part_name)
    if part_usage is None:
        raise ValueError(f"Unknown part '{part_name}' in connection")
    part_def = architecture.resolve_part(part_usage)
    if part_def is None:
        raise ValueError(f"Unresolved part definition for {part_name}")
    port_usage = part_def.ports.get(port_name)
    if port_usage is None:
        raise ValueError(f"Unknown port '{part_name}.{port_name}' in connection")
    port_def = architecture.resolve_port(port_usage)
    if port_def is None:
        raise ValueError("Port definition not connected")
    return port_def


def _parameter_set_source(set_name: str, prefix: str) -> str:
    prefix = prefix.strip().strip("/")
    return f"{prefix}/{set_name}.ssv" if prefix else f"{set_name}.ssv"


def _parameter_binding(
    spec: MappingSpec, parameter_set_prefix: str
) -> ParameterBinding:
    source = _parameter_set_source(spec.set_name, parameter_set_prefix)
    if spec.identity:
        return ParameterBinding(source=source, prefix=f"{spec.component_name}.")

    mapping = Ssp1ParameterMapping(version="1.0")
    for source_name, target_name in spec.entries:
        mapping.add_mapping(source_name, target_name)
    return ParameterBinding(
        source=source,
        parameter_mapping=Ssd1ParameterMappingReference(mapping=mapping),
    )


def _add_part_connectors(
    element,
    part_def: PartDefinition,
    architecture: Architecture,
    parameter_model: bool,
    *,
    is_system: bool,
) -> None:
    """Append port and parameter connectors for one component or system."""
    for port_usage in part_def.ports.values():
        port_def = architecture.resolve_port(port_usage)
        if port_def is None:
            raise ValueError(
                f"Unresolved port definition for "
                f"{part_def.name}.{port_usage.name}"
            )
        flat = bool(port_def.attributes.get(FLAT_CONNECTOR_ATTR))
        for attribute in port_def.attributes.values():
            if is_control_attribute(attribute.name):
                continue
            connector_name = (
                port_usage.name
                if flat
                else f"{port_usage.name}.{attribute.name}"
            )
            element.connectors.append(
                Connector(
                    name=connector_name,
                    kind=to_fmi_direction_definition(port_usage.direction),
                    type_name=attribute.effective_type_name,
                )
            )

    has_interface = parameter_interface(architecture, part_def) is not None
    if parameter_model and has_interface:
        for attribute in parameter_declarations(architecture, part_def):
            for item in parameter_items(attribute):
                element.connectors.append(
                    Connector(
                        name=item.name,
                        kind="parameter",
                        type_name=item.type_name,
                    )
                )
    elif not parameter_model and not is_system:
        for attrib_name, attribute in part_def.attributes.items():
            if is_control_attribute(attrib_name):
                continue
            for idx, _ in attribute.enumerator():
                name = (
                    f"{attrib_name}[{idx}]"
                    if attribute.is_list
                    else attrib_name
                )
                element.connectors.append(
                    Connector(
                        name=name,
                        kind="parameter",
                        type_name=attribute.effective_type_name,
                    )
                )


def _add_connections(
    target_system,
    part_def: PartDefinition,
    architecture: Architecture,
    type_check: bool,
) -> None:
    """Append this system level's connections to an SSD system."""
    for conn in part_def.connections.values():
        src_port_def = _endpoint_port_def(
            part_def, architecture, conn.source_part, conn.source_port
        )
        dst_port_def = _endpoint_port_def(
            part_def, architecture, conn.destination_part, conn.destination_port
        )
        if type_check and src_port_def is not dst_port_def:
            raise ValueError(
                f"Src {conn.source_port} and dest port "
                f"{conn.destination_port} must be same type"
            )

        src_flat = bool(src_port_def.attributes.get(FLAT_CONNECTOR_ATTR))
        dst_flat = bool(dst_port_def.attributes.get(FLAT_CONNECTOR_ATTR))
        for attribute_name in src_port_def.attributes.keys():
            if is_control_attribute(attribute_name):
                continue
            target_system.add_connection(
                Connection(
                    start_element=conn.source_part,
                    start_connector=(
                        conn.source_port
                        if src_flat
                        else f"{conn.source_port}.{attribute_name}"
                    ),
                    end_element=conn.destination_part,
                    end_connector=(
                        conn.destination_port
                        if dst_flat
                        else f"{conn.destination_port}.{attribute_name}"
                    ),
                )
            )


def _write_elements(
    parent,
    part_def: PartDefinition,
    architecture: Architecture,
    *,
    parameter_model: bool,
    type_check: bool,
) -> None:
    """Recursively write nested systems and leaf FMU components."""
    for part_name, part_usage in part_def.parts.items():
        child = architecture.resolve_part(part_usage)
        if child is None:
            raise ValueError(
                f"Unresolved part definition for {part_usage.name}"
            )
        if child.parts:
            implementation = child.attributes.get(IMPLEMENTATION_ATTR)
            if implementation is not None and implementation.value is not None:
                raise ValueError(
                    f"{child.name} has both subparts and "
                    f"'{IMPLEMENTATION_ATTR}'; a nested system cannot also be "
                    "an FMU component"
                )
            nested = System(name=part_name)
            parent.elements.append(nested)
            _add_part_connectors(
                nested,
                child,
                architecture,
                parameter_model,
                is_system=True,
            )
            _write_elements(
                nested,
                child,
                architecture,
                parameter_model=parameter_model,
                type_check=type_check,
            )
            continue

        component = Component()
        component.name = part_name
        component.component_type = "application/x-fmu-sharedlibrary"
        component.source = fmu_resource_path(child.name)
        implementation = child.attributes.get(IMPLEMENTATION_ATTR)
        if implementation is not None and implementation.value is not None:
            component.implementation = str(implementation.value)
        parent.elements.append(component)
        _add_part_connectors(
            component,
            child,
            architecture,
            parameter_model,
            is_system=False,
        )

    _add_connections(parent, part_def, architecture, type_check)


def build_ssd(
    ssd: SSD,
    system: PartDefinition,
    architecture: Architecture,
    type_check=True,
    parameter_set_prefix: str = "parameter_sets",
) -> None:
    ssd.xml.name = system.name
    ssd.xml.version = "1.0"

    if parameter_interface(architecture, system) is not None:
        raise ValueError(
            "Top-level composition parameter interfaces are not supported; "
            "attach parameter interfaces to component usages"
        )

    parameter_model = has_parameter_dialect(architecture, system)
    specs = []
    if parameter_model:
        validate_parameter_dialect(architecture, system)
        specs = mapping_specs(architecture, system)

    top = System(name=system.name)
    ssd.xml.system = top
    _add_part_connectors(
        top, system, architecture, parameter_model, is_system=True
    )
    _write_elements(
        top,
        system,
        architecture,
        parameter_model=parameter_model,
        type_check=type_check,
    )

    start = system.attributes.get(DEFAULT_START_ATTR)
    stop = system.attributes.get(DEFAULT_STOP_ATTR)
    ssd.xml.default_experiment = DefaultExperiment(
        start_time=float(start.value) if start is not None else 0,
        stop_time=float(stop.value) if stop is not None else 3600,
    )

    if parameter_model:
        top.parameter_bindings = [
            _parameter_binding(spec, parameter_set_prefix) for spec in specs
        ]
    else:
        parameter_set = system.attributes.get(PARAMETER_SET_ATTR)
        if parameter_set is not None and parameter_set.value is not None:
            top.parameter_bindings = [
                ParameterBinding(source=str(parameter_set.value))
            ]


def generate_ssd(
    architecture_path: Path,
    output_path: Path,
    composition: str,
    type_check=True,
    parameter_set_prefix: str = "parameter_sets",
) -> Path:

    architecture = load(architecture_path)
    system = architecture.get_part_def(composition)
    ensure_parent_dir(output_path)
    with SSD(output_path, mode="w") as ssd:
        build_ssd(
            ssd,
            system,
            architecture,
            type_check,
            parameter_set_prefix=parameter_set_prefix,
        )
    return output_path
