"""Generic SSD generation helpers."""
from __future__ import annotations

from pathlib import Path

from pycps_sysmlv2 import SysMLPartDefinition, load_system
from pyssp_standard.common_content_ssc import TypeBoolean, TypeInteger, TypeReal, TypeString
from pyssp_standard.ssd import Component, Connection, Connector, DefaultExperiment, SSD, System

from pyssp_sysml2.fmi_helpers import fmu_resource_path, to_fmi_direction_definition
from pyssp_sysml2.paths import ensure_parent_dir


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


def build_ssd(ssd: SSD, system: SysMLPartDefinition) -> None:
    ssd.name = system.name
    ssd.version = "1.0"
    ssd.system = System(name=system.name)

    for part_name, part_ref in system.parts.items():
        part = part_ref.part_def
        component = Component()
        component.name = part_name
        component.component_type = "application/x-fmu-sharedlibrary"
        component.source = fmu_resource_path(part.name)

        for port_ref, _port_def, attribute in part.get_port_attributes():
            component.connectors.append(
                Connector(
                    name=f"{port_ref.name}.{attribute.name}",
                    kind=to_fmi_direction_definition(port_ref.direction),
                    type_=_type_from_primitive(attribute.type.as_string()),
                )
            )

        for attrib_name, attribute in part.attributes.items():
            for idx, _ in attribute.enumerator():
                name = f"{attrib_name}[{idx}]" if attribute.is_list() else attrib_name
                component.connectors.append(
                    Connector(
                        name=name,
                        kind="parameter",
                        type_=_type_from_primitive(attribute.type.as_string()),
                    )
                )

        ssd.system.elements.append(component)

    for conn in system.connections:
        if conn.src_port_def is not conn.dst_port_def:
            raise ValueError(
                f"Src {conn.src_port_def.name} and dest port {conn.dst_port_def.name} must be same type"
            )
        if conn.src_port_def is None:
            raise ValueError("Port definition not connected")

        for attribute_name in conn.src_port_def.attributes.keys():
            ssd.add_connection(
                Connection(
                    start_element=conn.src_component,
                    start_connector=f"{conn.src_port}.{attribute_name}",
                    end_element=conn.dst_component,
                    end_connector=f"{conn.dst_port}.{attribute_name}",
                )
            )

    default_experiment = DefaultExperiment()
    default_experiment.start_time = 0
    default_experiment.stop_time = 3600
    ssd.default_experiment = default_experiment


def generate_ssd(architecture_path: Path, output_path: Path, composition: str) -> Path:
    system = load_system(architecture_path, composition)
    ensure_parent_dir(output_path)
    with SSD(output_path, mode="w") as ssd:
        build_ssd(ssd, system)
    return output_path
