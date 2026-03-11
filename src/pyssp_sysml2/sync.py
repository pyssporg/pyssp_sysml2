"""Sync helpers to apply SSD composition changes back into SysML."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Mapping, Tuple

from pycps_sysmlv2 import NodeType
from pyssp_standard.ssd import Component, SSD

from pyssp_sysml2.fmi_helpers import fmu_resource_path
from pyssp_sysml2.paths import ensure_parent_dir


def _load_architecture(architecture_path: Path):
    try:
        from pycps_sysmlv2 import SysMLParser
    except ImportError as exc:  # pragma: no cover - dependency contract
        raise RuntimeError("pycps_sysmlv2 must provide SysMLParser for sync support") from exc
    return SysMLParser(architecture_path).parse()


def _load_ssd_system(ssd_path: Path):
    with SSD(ssd_path, mode="r") as ssd:
        if ssd.system is None:
            raise ValueError(f"No system element found in SSD: {ssd_path}")
        return ssd.system


def _type_name_from_connector(connector) -> str:
    type_name = connector.type_.__class__.__name__
    if type_name.startswith("Type"):
        return type_name[4:]
    return "Real"


def _part_name_from_component(component: Component) -> str:
    if component.source:
        return Path(component.source).stem
    if component.name:
        return component.name
    raise ValueError("SSD component without a name cannot be synced")


def _build_architecture_from_ssd(ssd_system, composition: str):
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

    components = _index_components(ssd_system)
    endpoint_attributes: dict[tuple[str, str], dict[str, str]] = {}
    endpoint_directions: dict[tuple[str, str], str] = {}

    for component in components.values():
        for connector in component.connectors:
            if "." not in connector.name:
                continue
            port_name, attribute_name = _split_connector(connector.name)
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
        src_port, src_attr = _split_connector(connection.start_connector)
        dst_port, dst_attr = _split_connector(connection.end_connector)
        endpoint_attributes.setdefault((connection.start_element, src_port), {}).setdefault(
            src_attr, "Real"
        )
        endpoint_attributes.setdefault((connection.end_element, dst_port), {}).setdefault(
            dst_attr, "Real"
        )
        endpoint_directions.setdefault((connection.start_element, src_port), "out")
        endpoint_directions.setdefault((connection.end_element, dst_port), "in")

    architecture = SysMLPackage(name="RecoveredFromSSD", package="RecoveredFromSSD")
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
            attrs = endpoint_attributes[endpoint]
            signature = tuple(sorted(attrs.items()))
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

    grouped: Dict[Tuple[str, str, str, str], set[str]] = {}
    for connection in ssd_system.connections:
        src_port, src_attr = _split_connector(connection.start_connector)
        dst_port, _ = _split_connector(connection.end_connector)
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


def _split_connector(name: str) -> tuple[str, str]:
    if "." not in name:
        raise ValueError(f"Connector '{name}' is not in 'port.attribute' form")
    return name.split(".", 1)


def _index_components(ssd_system) -> dict[str, Component]:
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


def _resolve_component_part_definition(architecture, system, component: Component):
    existing = system.refs(NodeType.Part).get(component.name)
    existing_part_def = None if existing is None else existing.ref_node
    if existing is not None and existing_part_def is not None:
        if component.source is None or component.source == fmu_resource_path(existing.type):
            return existing.type, existing_part_def

    if component.source is None:
        raise ValueError(
            f"SSD component '{component.name}' is missing a source, so its SysML part definition cannot be resolved"
        )

    matches = [
        part_def
        for part_def in architecture.defs(NodeType.Part).values()
        if fmu_resource_path(part_def.name) == component.source
    ]
    if not matches:
        raise ValueError(
            f"SSD component '{component.name}' references unknown part source '{component.source}'"
        )
    if len(matches) > 1:
        raise ValueError(
            f"SSD component '{component.name}' source '{component.source}' is ambiguous across part definitions"
        )
    part_def = matches[0]
    return part_def.name, part_def


def _derive_target_parts(architecture, system, ssd_system) -> dict[str, object]:
    from pycps_sysmlv2 import SysMLPartReference

    components = _index_components(ssd_system)
    target_parts = {}
    for component_name in sorted(components):
        component = components[component_name]
        part_name, part_def = _resolve_component_part_definition(architecture, system, component)
        existing = system.refs(NodeType.Part).get(component_name)
        if (
            existing is not None
            and existing.type == part_name
            and existing.ref_node is part_def
        ):
            target_parts[component_name] = existing
            continue

        target_parts[component_name] = SysMLPartReference(
            name=component_name,
            type=part_name,
            ref_node=part_def,
            doc=getattr(existing, "doc", None),
        )
    return target_parts


def _derive_port_connections_from_ssd(
    target_parts: Mapping[str, object],
    ssd_system,
) -> set[Tuple[str, str, str, str]]:
    grouped: Dict[Tuple[str, str, str, str], set[str]] = {}
    for conn in ssd_system.connections:
        src_port, src_attr = _split_connector(conn.start_connector)
        dst_port, dst_attr = _split_connector(conn.end_connector)
        if src_attr != dst_attr:
            raise ValueError(
                "SSD uses attribute remapping that cannot be represented as a SysML port connect: "
                f"{conn.start_element}.{conn.start_connector} -> {conn.end_element}.{conn.end_connector}"
            )
        key = (conn.start_element, src_port, conn.end_element, dst_port)
        grouped.setdefault(key, set()).add(src_attr)

    target: set[Tuple[str, str, str, str]] = set()
    for src_component, src_port, dst_component, dst_port in grouped:
        if src_component not in target_parts:
            raise ValueError(f"SSD references unknown source component '{src_component}'")
        if dst_component not in target_parts:
            raise ValueError(f"SSD references unknown destination component '{dst_component}'")

        src_part = target_parts[src_component].ref_node
        dst_part = target_parts[dst_component].ref_node
        if src_part is None or dst_part is None:
            raise ValueError("Could not resolve part definition for at least one SSD connection endpoint")
        if src_port not in src_part.refs(NodeType.Port):
            raise ValueError(f"Unknown source port '{src_component}.{src_port}' in SSD")
        if dst_port not in dst_part.refs(NodeType.Port):
            raise ValueError(f"Unknown destination port '{dst_component}.{dst_port}' in SSD")

        src_port_def = src_part.refs(NodeType.Port)[src_port].ref_node
        dst_port_def = dst_part.refs(NodeType.Port)[dst_port].ref_node
        if src_port_def is None or dst_port_def is None:
            raise ValueError("Could not resolve port definition for at least one SSD connection endpoint")
        if src_port_def is not dst_port_def:
            raise ValueError(
                "SSD connects incompatible ports that cannot be represented in SysML composition: "
                f"{src_component}.{src_port} -> {dst_component}.{dst_port}"
            )

        required_attributes = set(src_port_def.defs(NodeType.Attribute).keys())
        actual_attributes = grouped[(src_component, src_port, dst_component, dst_port)]
        if required_attributes != actual_attributes:
            missing = sorted(required_attributes - actual_attributes)
            extra = sorted(actual_attributes - required_attributes)
            raise ValueError(
                "SSD contains a partial/invalid attribute mapping for port connection "
                f"{src_component}.{src_port} -> {dst_component}.{dst_port}. "
                f"missing={missing}, extra={extra}"
            )

        target.add((src_component, src_port, dst_component, dst_port))

    return target


def _connection_key(src_component: str, src_port: str, dst_component: str, dst_port: str) -> str:
    return f"{src_component}.{src_port}->{dst_component}.{dst_port}"


def _replace_system_parts(system, target_parts: Mapping[str, object]) -> None:
    for key in list(system.refs(NodeType.Part).keys()):
        system.remove_ref(NodeType.Part, key)
    for key, part_ref in target_parts.items():
        part_ref.parent = system
        system.add_ref(NodeType.Part, key, part_ref, overwrite_warning=False)


def _replace_system_connections(
    system,
    target_parts: Mapping[str, object],
    target_connections: Iterable[Tuple[str, str, str, str]],
) -> None:
    from pycps_sysmlv2 import SysMLConnection

    previous = system.defs(NodeType.Connection)
    updated = {}
    for src_component, src_port, dst_component, dst_port in sorted(target_connections):
        key = _connection_key(src_component, src_port, dst_component, dst_port)
        existing = previous.get(key)
        if existing is not None:
            updated[key] = existing
            continue
        updated[key] = SysMLConnection(
            name=f"{src_component}.{src_port}_to_{dst_component}.{dst_port}",
            src_part=src_component,
            src_port=src_port,
            dst_part=dst_component,
            dst_port=dst_port,
            src_part_node=target_parts[src_component],
            dst_part_node=target_parts[dst_component],
            src_port_node=target_parts[src_component].ref_node.refs(NodeType.Port)[src_port],
            dst_port_node=target_parts[dst_component].ref_node.refs(NodeType.Port)[dst_port],
        )

    for key in list(system.defs(NodeType.Connection).keys()):
        system.remove_def(NodeType.Connection, key)
    for key, connection in updated.items():
        system.add_def(NodeType.Connection, key, connection, overwrite_warning=False)


def sync_sysml_from_ssd(
    architecture_path: Path,
    ssd_path: Path,
    composition: str,
    output_architecture_dir: Path | None = None,
) -> list[Path]:
    """Apply SSD composition edits to a SysML architecture and write updated .sysml files."""
    ssd_system = _load_ssd_system(ssd_path)
    try:
        architecture = _load_architecture(architecture_path)
        system = architecture.get_def(NodeType.Part, composition)
    except FileNotFoundError:
        architecture, system = _build_architecture_from_ssd(ssd_system, composition)

    target_parts = _derive_target_parts(architecture, system, ssd_system)
    target_connections = _derive_port_connections_from_ssd(target_parts, ssd_system)
    _replace_system_parts(system, target_parts)
    _replace_system_connections(system, target_parts, target_connections)

    written: list[Path] = []
    output_root = output_architecture_dir or (
        architecture_path if architecture_path.is_dir() else architecture_path.parent
    )
    file_texts = architecture.export_declared()
    for file_name, content in file_texts.items():
        output_path = output_root / file_name
        ensure_parent_dir(output_path)
        output_path.write_text(content, encoding="utf-8")
        written.append(output_path)

    return sorted(written)
