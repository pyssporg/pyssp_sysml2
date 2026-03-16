"""Helpers for generating minimal SysML models from SSD files."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable

from pycps_sysmlv2 import NodeType
from pyssp_standard.ssd import Component, SSD

from pyssp_sysml2.paths import ensure_parent_dir, DEFAULT_PACKAGE_NAME

SCALAR_ATTRIBUTE_NAME = "value"


def load_ssd_system(ssd_path: Path):
    with SSD(ssd_path, mode="r") as ssd:
        if ssd.system is None:
            raise ValueError(f"No system element found in SSD: {ssd_path}")
        return ssd.system


def split_connector(name: str) -> tuple[str, str]:
    if "." not in name:
        raise ValueError(f"Connector '{name}' is not in 'port.attribute' form")
    return name.split(".", 1)


def split_connector_or_scalar(name: str) -> tuple[str, str]:
    if "." not in name:
        return name, SCALAR_ATTRIBUTE_NAME
    return name.split(".", 1)


def index_components(ssd_system) -> dict[str, Component]:
    components: dict[str, Component] = {}
    for element in ssd_system.elements:
        if not isinstance(element, Component):
            raise ValueError("Nested SSD systems are not supported for SysML sync")
        if not element.name:
            raise ValueError("SSD component without a name cannot be synced")
        if element.name in components:
            raise ValueError(f"SSD contains duplicate component '{element.name}'")
        components[element.name] = element
    return components


def _type_name_from_connector(connector) -> str:
    type_name = connector.type_.__class__.__name__
    if type_name.startswith("Type"):
        type_name = type_name[4:]
    if type_name == "Enumeration":
        return "Integer"
    if type_name in {"Real", "Integer", "Boolean", "String"}:
        return type_name
    return "Real"


def _merge_type_names(type_names: Iterable[str]) -> str:
    known_type_names = [name for name in type_names if name != "Unknown"]
    if not known_type_names:
        return "Real"
    if "Real" in known_type_names:
        return "Real"
    if "Integer" in known_type_names:
        return "Integer"
    if "Boolean" in known_type_names:
        return "Boolean"
    if "String" in known_type_names:
        return "String"
    return known_type_names[0]


def _find(parent: dict[tuple[str, str], tuple[str, str]], item: tuple[str, str]) -> tuple[str, str]:
    root = parent.setdefault(item, item)
    if root != item:
        parent[item] = _find(parent, root)
    return parent[item]


def _union(
    parent: dict[tuple[str, str], tuple[str, str]],
    left: tuple[str, str],
    right: tuple[str, str],
) -> None:
    left_root = _find(parent, left)
    right_root = _find(parent, right)
    if left_root != right_root:
        parent[right_root] = left_root


def _group_endpoints(
    endpoint_attributes: dict[tuple[str, str], dict[str, str]],
    ssd_system,
) -> dict[tuple[str, str], tuple[str, str]]:
    parent: dict[tuple[str, str], tuple[str, str]] = {
        endpoint: endpoint for endpoint in endpoint_attributes
    }
    for connection in ssd_system.connections:
        src_port, _ = split_connector_or_scalar(connection.start_connector)
        dst_port, _ = split_connector_or_scalar(connection.end_connector)
        _union(parent, (connection.start_element, src_port), (connection.end_element, dst_port))
    return {endpoint: _find(parent, endpoint) for endpoint in endpoint_attributes}


def _canonicalize_group_signatures(
    endpoint_attributes: dict[tuple[str, str], dict[str, str]],
    endpoint_groups: dict[tuple[str, str], tuple[str, str]],
) -> dict[tuple[str, str], tuple[tuple[str, str], ...]]:
    grouped_endpoints: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for endpoint, group in endpoint_groups.items():
        grouped_endpoints.setdefault(group, []).append(endpoint)

    group_signatures: dict[tuple[str, str], tuple[tuple[str, str], ...]] = {}
    for group, endpoints in grouped_endpoints.items():
        raw_attributes = [endpoint_attributes[endpoint] for endpoint in endpoints]
        is_scalar_group = all(len(attrs) <= 1 for attrs in raw_attributes)
        merged_types: dict[str, list[str]] = {}
        for attrs in raw_attributes:
            for attr_name, attr_type in attrs.items():
                canonical_name = SCALAR_ATTRIBUTE_NAME if is_scalar_group else attr_name
                merged_types.setdefault(canonical_name, []).append(attr_type)
        group_signatures[group] = tuple(
            sorted(
                (attr_name, _merge_type_names(attr_types))
                for attr_name, attr_types in merged_types.items()
            )
        )
    return group_signatures


def _part_name_from_component(component: Component) -> str:
    if component.source:
        return Path(component.source).stem
    if component.name:
        return component.name
    raise ValueError("SSD component without a name cannot be synced")


def build_architecture_from_ssd(ssd_system, composition: str):
    from pycps_sysmlv2 import (
        SysMLAttribute,
        SysMLConnection,
        SysMLPackage,
        SysMLPartDefinition,
        SysMLPartReference,
        SysMLPortDefinition,
        SysMLPortReference,
        SysMLType,
    )

    components = index_components(ssd_system)
    endpoint_attributes: dict[tuple[str, str], dict[str, str]] = {}
    endpoint_directions: dict[tuple[str, str], str] = {}

    for component in components.values():
        for connector in component.connectors:
            port_name, attribute_name = split_connector_or_scalar(connector.name)
            endpoint = (component.name, port_name)
            endpoint_attributes.setdefault(endpoint, {})[attribute_name] = _type_name_from_connector(
                connector
            )
            if connector.kind == "output":
                endpoint_directions.setdefault(endpoint, "out")
            elif connector.kind == "input":
                endpoint_directions.setdefault(endpoint, "in")
            else:
                endpoint_directions.setdefault(endpoint, "in")

    for connection in ssd_system.connections:
        src_port, src_attr = split_connector_or_scalar(connection.start_connector)
        dst_port, dst_attr = split_connector_or_scalar(connection.end_connector)
        endpoint_attributes.setdefault((connection.start_element, src_port), {}).setdefault(
            src_attr, "Real"
        )
        endpoint_attributes.setdefault((connection.end_element, dst_port), {}).setdefault(
            dst_attr, "Real"
        )
        endpoint_directions.setdefault((connection.start_element, src_port), "out")
        endpoint_directions.setdefault((connection.end_element, dst_port), "in")

    endpoint_groups = _group_endpoints(endpoint_attributes, ssd_system)
    group_signatures = _canonicalize_group_signatures(endpoint_attributes, endpoint_groups)

    architecture = SysMLPackage(name=DEFAULT_PACKAGE_NAME, package=DEFAULT_PACKAGE_NAME)
    part_defs_by_name: dict[str, object] = {}
    component_part_defs: dict[str, object] = {}
    port_defs_by_signature: dict[tuple[tuple[str, str], ...], object] = {}

    for component_name in sorted(components):
        component = components[component_name]
        part_name = _part_name_from_component(component)
        part_def = part_defs_by_name.get(part_name)
        if part_def is None:
            part_def = SysMLPartDefinition(name=part_name, source_file="architecture.sysml")
            part_def.parent = architecture
            architecture.add_def(NodeType.Part, part_def.name, part_def)
            part_defs_by_name[part_name] = part_def
        component_part_defs[component_name] = part_def

        for endpoint in sorted(key for key in endpoint_attributes if key[0] == component_name):
            _, port_name = endpoint
            signature = group_signatures[endpoint_groups[endpoint]]
            port_def = port_defs_by_signature.get(signature)
            if port_def is None:
                port_def_name = f"Port_{len(port_defs_by_signature) + 1}"
                port_def = SysMLPortDefinition(name=port_def_name, source_file="architecture.sysml")
                for attr_name, attr_type in signature:
                    port_def.add_def(
                        NodeType.Attribute,
                        attr_name,
                        SysMLAttribute(
                            name=attr_name,
                            type=SysMLType.from_string(attr_type),
                            value=None,
                        ),
                    )
                port_def.parent = architecture
                architecture.add_def(NodeType.Port, port_def.name, port_def)
                port_defs_by_signature[signature] = port_def

            if port_name not in part_def.refs(NodeType.Port):
                port_ref = SysMLPortReference(
                    name=port_name,
                    direction=endpoint_directions.get(endpoint, "in"),
                    type=port_def.name,
                    ref_node=port_def,
                )
                port_ref.parent = part_def
                part_def.add_ref(NodeType.Port, port_name, port_ref)

    system = SysMLPartDefinition(name=composition, source_file="architecture.sysml")
    system.parent = architecture
    architecture.add_def(NodeType.Part, system.name, system)
    for component_name in sorted(components):
        part_def = component_part_defs[component_name]
        part_ref = SysMLPartReference(
            name=component_name,
            type=part_def.name,
            ref_node=part_def,
        )
        part_ref.parent = system
        system.add_ref(NodeType.Part, component_name, part_ref)

    grouped: Dict[tuple[str, str, str, str], set[str]] = {}
    for connection in ssd_system.connections:
        src_port, src_attr = split_connector_or_scalar(connection.start_connector)
        dst_port, _ = split_connector_or_scalar(connection.end_connector)
        key = (connection.start_element, src_port, connection.end_element, dst_port)
        grouped.setdefault(key, set()).add(src_attr)

    for src_component, src_port, dst_component, dst_port in sorted(grouped):
        src_part_ref = system.refs(NodeType.Part)[src_component]
        dst_part_ref = system.refs(NodeType.Part)[dst_component]
        src_part_def = src_part_ref.ref_node
        dst_part_def = dst_part_ref.ref_node
        connection = SysMLConnection(
            name=f"{src_component}.{src_port}_to_{dst_component}.{dst_port}",
            src_part=src_component,
            src_port=src_port,
            dst_part=dst_component,
            dst_port=dst_port,
            src_part_node=src_part_ref,
            dst_part_node=dst_part_ref,
            src_port_node=src_part_def.refs(NodeType.Port)[src_port],
            dst_port_node=dst_part_def.refs(NodeType.Port)[dst_port],
        )
        system.add_def(NodeType.Connection, connection.key, connection)

    return architecture, system


def generate_sysml_from_ssd(
    ssd_path: Path,
    output_path: Path,
    composition: str | None = None,
) -> Path:
    ssd_system = load_ssd_system(ssd_path)
    composition_name = composition or getattr(ssd_system, "name", None)
    if not composition_name:
        raise ValueError("Composition name must be provided or present on the SSD system")

    architecture, _ = build_architecture_from_ssd(ssd_system, composition_name)
    file_texts = architecture.export_declared()
    if len(file_texts) != 1:
        raise ValueError("SSD-to-SysML generation expected a single exported architecture file")

    content = next(iter(file_texts.values()))
    ensure_parent_dir(output_path)
    output_path.write_text(content, encoding="utf-8")
    return output_path
