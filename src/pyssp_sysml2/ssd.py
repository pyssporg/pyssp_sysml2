"""Generic SSD generation helpers."""

from __future__ import annotations

from pathlib import Path

from pycps_sysmlv2 import NodeType, SysMLPartDefinition, SysMLParser
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


def build_ssd(ssd: SSD, system: SysMLPartDefinition, type_check=True) -> None:
    ssd.name = system.name
    ssd.version = "1.0"
    ssd.system = System(name=system.name)

    for part_name, part_ref in system.refs(NodeType.Part).items():
        part = part_ref.ref_node
        component = Component()
        component.name = part_name
        component.component_type = "application/x-fmu-sharedlibrary"
        component.source = fmu_resource_path(part.name)

        for port_ref in part.refs(NodeType.Port).values():
            port_def = port_ref.ref_node
            if port_def is None:
                raise ValueError(
                    f"Unresolved port definition for {part.name}.{port_ref.name}"
                )
            for attribute in port_def.defs(NodeType.Attribute).values():
                component.connectors.append(
                    Connector(
                        name=f"{port_ref.name}.{attribute.name}",
                        kind=to_fmi_direction_definition(port_ref.direction),
                        type_=_type_from_primitive(attribute.type.as_string()),
                    )
                )

        for attrib_name, attribute in part.defs(NodeType.Attribute).items():
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

    for conn in system.defs(NodeType.Connection).values():
        src_port_def = (
            None if conn.src_port_node is None else conn.src_port_node.ref_node
        )
        dst_port_def = (
            None if conn.dst_port_node is None else conn.dst_port_node.ref_node
        )
        if type_check and src_port_def is not dst_port_def:
            raise ValueError(
                f"Src {conn.src_port_node.name} and dest port {conn.dst_port_node.name} must be same type"
            )
        if conn.src_port_node is None:
            raise ValueError("Port definition not connected")
        if src_port_def is None:
            raise ValueError("Port definition not connected")

        for attribute_name in src_port_def.defs(NodeType.Attribute).keys():
            ssd.add_connection(
                Connection(
                    start_element=conn.src_part,
                    start_connector=f"{conn.src_port}.{attribute_name}",
                    end_element=conn.dst_part,
                    end_connector=f"{conn.dst_port}.{attribute_name}",
                )
            )

    default_experiment = DefaultExperiment()
    default_experiment.start_time = 0
    default_experiment.stop_time = 3600
    ssd.default_experiment = default_experiment


def generate_ssd(
    architecture_path: Path, output_path: Path, composition: str, type_check=True
) -> Path:

    arch = SysMLParser(architecture_path).parse()
    system = arch.get_def(NodeType.Part, composition)
    ensure_parent_dir(output_path)
    with SSD(output_path, mode="w") as ssd:
        build_ssd(ssd, system, type_check)
    return output_path
