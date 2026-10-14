"""Generic SSD generation helpers."""

from __future__ import annotations

from pathlib import Path

from pyssp_standard.common_content_ssc import (
    TypeBoolean,
    TypeInteger,
    TypeReal,
    TypeString,
)
from pyssp_standard.ssd import (
    Component,
    Connection,
    Connector,
    DefaultExperiment,
    SSD,
    System,
)

from pyssp_sysml2.fmi_helpers import fmu_resource_path, to_fmi_direction_definition
from pyssp_sysml2.paths import ensure_parent_dir
from pyssp_sysml2.sysml_model import Architecture, PartDefinition, load


def _type_from_primitive(type_name: str):
    if type_name == "Real":
        return TypeReal(unit=None)
    if type_name == "Integer":
        return TypeInteger()
    if type_name == "Boolean":
        return TypeBoolean()
    if type_name == "String":
        return TypeString()
    return TypeReal(unit=None)


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
    ssd.name = system.name
    ssd.version = "1.0"
    ssd.system = System(name=system.name)

    for part_name, part_usage in system.parts.items():
        part = architecture.resolve_part(part_usage)
        if part is None:
            raise ValueError(f"Unresolved part definition for {part_usage.name}")
        component = Component()
        component.name = part_name
        component.component_type = "application/x-fmu-sharedlibrary"
        component.source = fmu_resource_path(part.name)

        for port_usage in part.ports.values():
            port_def = architecture.resolve_port(port_usage)
            if port_def is None:
                raise ValueError(
                    f"Unresolved port definition for {part.name}.{port_usage.name}"
                )
            for attribute in port_def.attributes.values():
                component.connectors.append(
                    Connector(
                        name=f"{port_usage.name}.{attribute.name}",
                        kind=to_fmi_direction_definition(port_usage.direction),
                        type_=_type_from_primitive(attribute.effective_type_name),
                    )
                )

        for attrib_name, attribute in part.attributes.items():
            for idx, _ in attribute.enumerator():
                name = f"{attrib_name}[{idx}]" if attribute.is_list else attrib_name
                component.connectors.append(
                    Connector(
                        name=name,
                        kind="parameter",
                        type_=_type_from_primitive(attribute.effective_type_name),
                    )
                )

        ssd.system.elements.append(component)

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

        for attribute_name in src_port_def.attributes.keys():
            ssd.add_connection(
                Connection(
                    start_element=conn.source_part,
                    start_connector=f"{conn.source_port}.{attribute_name}",
                    end_element=conn.destination_part,
                    end_connector=f"{conn.destination_port}.{attribute_name}",
                )
            )

    default_experiment = DefaultExperiment()
    default_experiment.start_time = 0
    default_experiment.stop_time = 3600
    ssd.default_experiment = default_experiment


def generate_ssd(
    architecture_path: Path, output_path: Path, composition: str, type_check=True
) -> Path:

    architecture = load(architecture_path)
    system = architecture.get_part_def(composition)
    ensure_parent_dir(output_path)
    with SSD(output_path, mode="w") as ssd:
        build_ssd(ssd, system, architecture, type_check)
    return output_path
