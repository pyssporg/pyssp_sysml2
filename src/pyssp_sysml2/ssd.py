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

from pyssp_sysml2.fmi_helpers import fmu_resource_path, to_fmi_direction_definition
from pyssp_sysml2.paths import ensure_parent_dir
from pyssp_sysml2.sysml import (
    DEFAULT_START_ATTR,
    DEFAULT_STOP_ATTR,
    FLAT_CONNECTOR_ATTR,
    IMPLEMENTATION_ATTR,
    PARAMETER_SET_ATTR,
    is_control_attribute,
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


def build_ssd(
    ssd: SSD,
    system: PartDefinition,
    architecture: Architecture,
    type_check=True,
) -> None:
    ssd.xml.name = system.name
    ssd.xml.version = "1.0"
    ssd.xml.system = System(name=system.name)

    for part_name, part_usage in system.parts.items():
        part = architecture.resolve_part(part_usage)
        if part is None:
            raise ValueError(f"Unresolved part definition for {part_usage.name}")
        component = Component()
        component.name = part_name
        component.component_type = "application/x-fmu-sharedlibrary"
        component.source = fmu_resource_path(part.name)
        implementation = part.attributes.get(IMPLEMENTATION_ATTR)
        if implementation is not None and implementation.value is not None:
            component.implementation = str(implementation.value)

        for port_usage in part.ports.values():
            port_def = architecture.resolve_port(port_usage)
            if port_def is None:
                raise ValueError(
                    f"Unresolved port definition for {part.name}.{port_usage.name}"
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
                component.connectors.append(
                    Connector(
                        name=connector_name,
                        kind=to_fmi_direction_definition(port_usage.direction),
                        type_name=attribute.effective_type_name,
                    )
                )

        for attrib_name, attribute in part.attributes.items():
            if is_control_attribute(attrib_name):
                continue
            for idx, _ in attribute.enumerator():
                name = f"{attrib_name}[{idx}]" if attribute.is_list else attrib_name
                component.connectors.append(
                    Connector(
                        name=name,
                        kind="parameter",
                        type_name=attribute.effective_type_name,
                    )
                )

        ssd.xml.system.elements.append(component)

    for conn in system.connections.values():
        src_port_def = _endpoint_port_def(
            system, architecture, conn.source_part, conn.source_port
        )
        dst_port_def = _endpoint_port_def(
            system, architecture, conn.destination_part, conn.destination_port
        )
        if type_check and src_port_def is not dst_port_def:
            raise ValueError(
                f"Src {conn.source_port} and dest port {conn.destination_port} must be same type"
            )

        src_flat = bool(src_port_def.attributes.get(FLAT_CONNECTOR_ATTR))
        dst_flat = bool(dst_port_def.attributes.get(FLAT_CONNECTOR_ATTR))
        for attribute_name in src_port_def.attributes.keys():
            if is_control_attribute(attribute_name):
                continue
            ssd.xml.system.add_connection(
                Connection(
                    start_element=conn.source_part,
                    start_connector=(
                        conn.source_port if src_flat else f"{conn.source_port}.{attribute_name}"
                    ),
                    end_element=conn.destination_part,
                    end_connector=(
                        conn.destination_port
                        if dst_flat
                        else f"{conn.destination_port}.{attribute_name}"
                    ),
                )
            )

    start = system.attributes.get(DEFAULT_START_ATTR)
    stop = system.attributes.get(DEFAULT_STOP_ATTR)
    ssd.xml.default_experiment = DefaultExperiment(
        start_time=float(start.value) if start is not None else 0,
        stop_time=float(stop.value) if stop is not None else 3600,
    )

    parameter_set = system.attributes.get(PARAMETER_SET_ATTR)
    if parameter_set is not None and parameter_set.value is not None:
        ssd.xml.system.parameter_bindings = [
            ParameterBinding(source=str(parameter_set.value))
        ]


def generate_ssd(
    architecture_path: Path, output_path: Path, composition: str, type_check=True
) -> Path:

    architecture = load(architecture_path)
    system = architecture.get_part_def(composition)
    ensure_parent_dir(output_path)
    with SSD(output_path, mode="w") as ssd:
        build_ssd(ssd, system, architecture, type_check)
    return output_path
