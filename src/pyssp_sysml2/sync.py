"""Sync helpers to apply SSD composition changes back into SysML."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Mapping, Tuple

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
from pyssp_sysml2.sysml_model import (
    Architecture,
    Attribute,
    Connection,
    PartDefinition,
    PartUsage,
    PortDefinition,
    PortUsage,
    load,
)

INFERRED_PARTS_FILENAME = "inferred_external_parts.sysml"


def _load_architecture(architecture_path: Path) -> Architecture:
    return load(architecture_path)


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


def _port_def_signature(port_def: PortDefinition) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted((attr.name, attr.effective_type_name) for attr in port_def.attributes.values())
    )


def _find_port_def_by_signature(architecture: Architecture, signature):
    for port_def in architecture.port_definitions.values():
        if _port_def_signature(port_def) == signature:
            return port_def
    return None


def _synthesize_component_part_def(
    architecture: Architecture, component: Component
) -> tuple[str, PartDefinition]:
    """Create a part definition from an SSD component that references an unknown FMU source.

    The part definition name is taken from the component's FMU source stem. Ports are
    collected from the component's connectors and matched by signature against existing
    port definitions in the architecture; unmatched signatures get a new port definition.
    Synthesized definitions are exported into ``inferred_external_parts.sysml``.
    """
    part_name = _part_name_from_component(component)
    existing_part_def = architecture.part_definitions.get(part_name)
    if existing_part_def is not None:
        return existing_part_def.name, existing_part_def

    part_def = PartDefinition(name=part_name, source_file=INFERRED_PARTS_FILENAME)
    architecture.add_part_def(part_def)

    port_attributes, port_directions = _collect_component_ports(component)
    for port_name in sorted(port_attributes):
        signature = _port_signature(port_attributes[port_name])
        port_def = _find_port_def_by_signature(architecture, signature)
        if port_def is None:
            port_def_name = f"Port_{len(architecture.port_definitions) + 1}"
            port_def = PortDefinition(
                name=port_def_name,
                source_file=INFERRED_PARTS_FILENAME,
            )
            for attr_name, attr_type in signature:
                port_def.attributes[attr_name] = Attribute(
                    name=attr_name,
                    type_name=attr_type,
                    value=None,
                )
            architecture.add_port_def(port_def)

        part_def.ports[port_name] = PortUsage(
            name=port_name,
            direction=port_directions.get(port_name, "in"),
            type_name=port_def.name,
        )

    return part_name, part_def


def _resolve_component_part_definition(
    architecture: Architecture,
    system: PartDefinition,
    component: Component,
    *,
    synthesize_external_parts: bool = True,
):
    existing = system.parts.get(component.name)
    existing_part_def = None if existing is None else architecture.resolve_part(existing)
    if existing is not None and existing_part_def is not None:
        if component.source is None or component.source == fmu_resource_path(existing.type_name):
            return existing.type_name, existing_part_def

    if component.source is None:
        raise ValueError(
            f"SSD component '{component.name}' is missing a source, so its SysML part definition cannot be resolved"
        )

    matches = [
        part_def
        for part_def in architecture.part_definitions.values()
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
    architecture: Architecture,
    system: PartDefinition,
    ssd_system,
    *,
    synthesize_external_parts: bool = True,
) -> dict[str, PartUsage]:
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
        existing = system.parts.get(component_name)
        if (
            existing is not None
            and existing.type_name == part_name
            and architecture.resolve_part(existing) is part_def
        ):
            target_parts[component_name] = existing
            continue

        target_parts[component_name] = PartUsage(
            name=component_name,
            type_name=part_name,
            doc=getattr(existing, "doc", None),
        )
    return target_parts


def _derive_port_connections_from_ssd(
    target_parts: Mapping[str, PartUsage],
    ssd_system,
    architecture: Architecture,
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

        src_part = architecture.resolve_part(target_parts[src_component])
        dst_part = architecture.resolve_part(target_parts[dst_component])
        if src_part is None or dst_part is None:
            raise ValueError("Could not resolve part definition for at least one SSD connection endpoint")
        src_port_usage = src_part.ports.get(src_port)
        dst_port_usage = dst_part.ports.get(dst_port)
        if src_port_usage is None:
            raise ValueError(f"Unknown source port '{src_component}.{src_port}' in SSD")
        if dst_port_usage is None:
            raise ValueError(f"Unknown destination port '{dst_component}.{dst_port}' in SSD")

        src_port_def = architecture.resolve_port(src_port_usage)
        dst_port_def = architecture.resolve_port(dst_port_usage)
        if src_port_def is None or dst_port_def is None:
            raise ValueError("Could not resolve port definition for at least one SSD connection endpoint")
        if src_port_def is not dst_port_def:
            raise ValueError(
                "SSD connects incompatible ports that cannot be represented in SysML composition: "
                f"{src_component}.{src_port} -> {dst_component}.{dst_port}"
            )

        required_attributes = set(src_port_def.attributes.keys())
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


def _replace_system_parts(system: PartDefinition, target_parts: Mapping[str, PartUsage]) -> None:
    system.parts.clear()
    system.parts.update(target_parts)


def _replace_system_connections(
    system: PartDefinition,
    target_connections: Iterable[Tuple[str, str, str, str]],
) -> None:
    previous = system.connections
    updated = {}
    for src_component, src_port, dst_component, dst_port in sorted(target_connections):
        key = _connection_key(src_component, src_port, dst_component, dst_port)
        existing = previous.get(key)
        if existing is not None:
            updated[key] = existing
            continue
        updated[key] = Connection(
            name=f"{src_component}.{src_port}_to_{dst_component}.{dst_port}",
            source_part=src_component,
            source_port=src_port,
            destination_part=dst_component,
            destination_port=dst_port,
        )

    system.connections.clear()
    system.connections.update(updated)


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
        system = architecture.get_part_def(composition)
    except FileNotFoundError:
        architecture, system = build_architecture_from_ssd(ssd_system, composition)

    target_parts = _derive_target_parts(
        architecture,
        system,
        ssd_system,
        synthesize_external_parts=synthesize_external_parts,
    )
    target_connections = _derive_port_connections_from_ssd(target_parts, ssd_system, architecture)
    _replace_system_parts(system, target_parts)
    _replace_system_connections(system, target_connections)

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
