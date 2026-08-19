"""Sync helpers to apply SSD composition changes back into SysML."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Mapping, Tuple

from pycps_sysmlv2 import NodeType
from pyssp_standard.ssd import Component

from pyssp_sysml2.fmi_helpers import fmu_resource_path
from pyssp_sysml2.paths import ensure_parent_dir
from pyssp_sysml2.sysml import (
    SCALAR_ATTRIBUTE_NAME,
    _merge_type_names,
    _part_name_from_component,
    _type_name_from_connector,
    build_architecture_from_ssd,
    index_components,
    load_ssd_system,
    split_connector,
    split_connector_or_scalar,
)

INFERRED_PARTS_FILENAME = "inferred_external_parts.sysml"


def _load_architecture(architecture_path: Path):
    try:
        from pycps_sysmlv2 import SysMLParser
    except ImportError as exc:  # pragma: no cover - dependency contract
        raise RuntimeError("pycps_sysmlv2 must provide SysMLParser for sync support") from exc
    return SysMLParser(architecture_path).parse()


def _collect_component_ports(component: Component) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    """Group a component's connectors into per-port attributes and directions."""
    port_attributes: dict[str, dict[str, str]] = {}
    port_directions: dict[str, str] = {}
    for connector in component.connectors:
        port_name, attr_name = split_connector_or_scalar(connector.name)
        port_attributes.setdefault(port_name, {})[attr_name] = _type_name_from_connector(connector)
        if connector.kind == "output":
            port_directions.setdefault(port_name, "out")
        else:
            port_directions.setdefault(port_name, "in")
    return port_attributes, port_directions


def _port_signature(port_attributes: dict[str, str]) -> tuple[tuple[str, str], ...]:
    """Canonical (attribute, type) signature for a port, mirroring build_architecture_from_ssd."""
    is_scalar = len(port_attributes) <= 1
    canonical = {
        SCALAR_ATTRIBUTE_NAME if is_scalar else attr_name: _merge_type_names([attr_type])
        for attr_name, attr_type in port_attributes.items()
    }
    return tuple(sorted(canonical.items()))


def _port_def_signature(port_def) -> tuple[tuple[str, str], ...]:
    attributes = port_def.defs(NodeType.Attribute)
    return tuple(sorted((attr.name, attr.type.as_string()) for attr in attributes.values()))


def _find_port_def_by_signature(architecture, signature):
    for port_def in architecture.defs(NodeType.Port).values():
        if _port_def_signature(port_def) == signature:
            return port_def
    return None


def _synthesize_component_part_def(architecture, component: Component) -> tuple[str, object]:
    """Create a part definition from an SSD component that references an unknown FMU source.

    The part definition name is taken from the component's FMU source stem. Ports are
    collected from the component's connectors and matched by signature against existing
    port definitions in the architecture; unmatched signatures get a new port definition.
    Synthesized definitions are exported into ``inferred_external_parts.sysml``.
    """
    from pycps_sysmlv2 import (
        SysMLAttribute,
        SysMLPartDefinition,
        SysMLPortDefinition,
        SysMLPortReference,
        SysMLType,
    )

    part_name = _part_name_from_component(component)
    existing_part_def = architecture.defs(NodeType.Part).get(part_name)
    if existing_part_def is not None:
        return existing_part_def.name, existing_part_def

    part_def = SysMLPartDefinition(name=part_name, source_file=INFERRED_PARTS_FILENAME)
    part_def.parent = architecture
    architecture.add_def(NodeType.Part, part_name, part_def)

    port_attributes, port_directions = _collect_component_ports(component)
    for port_name in sorted(port_attributes):
        signature = _port_signature(port_attributes[port_name])
        port_def = _find_port_def_by_signature(architecture, signature)
        if port_def is None:
            port_def_name = f"Port_{len(architecture.defs(NodeType.Port)) + 1}"
            port_def = SysMLPortDefinition(
                name=port_def_name,
                source_file=INFERRED_PARTS_FILENAME,
            )
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
            architecture.add_def(NodeType.Port, port_def_name, port_def)

        port_ref = SysMLPortReference(
            name=port_name,
            direction=port_directions.get(port_name, "in"),
            type=port_def.name,
            ref_node=port_def,
        )
        port_ref.parent = part_def
        part_def.add_ref(NodeType.Port, port_name, port_ref)

    return part_name, part_def


def _resolve_component_part_definition(
    architecture,
    system,
    component: Component,
    *,
    synthesize_external_parts: bool = True,
):
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
    if not matches and synthesize_external_parts:
        _, part_def = _synthesize_component_part_def(architecture, component)
        matches = [part_def]
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


def _derive_target_parts(
    architecture,
    system,
    ssd_system,
    *,
    synthesize_external_parts: bool = True,
) -> dict[str, object]:
    from pycps_sysmlv2 import SysMLPartReference

    components = index_components(ssd_system)
    target_parts = {}
    for component_name in sorted(components):
        component = components[component_name]
        part_name, part_def = _resolve_component_part_definition(
            architecture,
            system,
            component,
            synthesize_external_parts=synthesize_external_parts,
        )
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
        src_port, src_attr = split_connector(conn.start_connector)
        dst_port, dst_attr = split_connector(conn.end_connector)
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
    synthesize_external_parts: bool = True,
) -> list[Path]:
    """Apply SSD composition edits to a SysML architecture and write updated .sysml files."""
    ssd_system = load_ssd_system(ssd_path)
    try:
        architecture = _load_architecture(architecture_path)
        system = architecture.get_def(NodeType.Part, composition)
    except FileNotFoundError:
        architecture, system = build_architecture_from_ssd(ssd_system, composition)

    target_parts = _derive_target_parts(
        architecture,
        system,
        ssd_system,
        synthesize_external_parts=synthesize_external_parts,
    )
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
