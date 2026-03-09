"""Sync helpers to apply SSD composition changes back into SysML."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Mapping, Tuple

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
    existing = system.parts.get(component.name)
    if existing is not None and existing.part_def is not None:
        if component.source is None or component.source == fmu_resource_path(existing.part_name):
            return existing.part_name, existing.part_def

    if component.source is None:
        raise ValueError(
            f"SSD component '{component.name}' is missing a source, so its SysML part definition cannot be resolved"
        )

    matches = [
        part_def
        for part_def in architecture.part_definitions.values()
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
        existing = system.parts.get(component_name)
        if (
            existing is not None
            and existing.part_name == part_name
            and existing.part_def is part_def
        ):
            target_parts[component_name] = existing
            continue

        target_parts[component_name] = SysMLPartReference(
            name=component_name,
            part_name=part_name,
            part_def=part_def,
            doc=getattr(existing, "doc", None),
        )
    return target_parts


def _derive_port_connections_from_ssd(
    target_parts: Mapping[str, object],
    ssd_system,
) -> set[Tuple[str, str, str, str]]:
    ssd_connections = ssd_system.connections

    grouped: Dict[Tuple[str, str, str, str], set[str]] = {}
    for conn in ssd_connections:
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

        src_part = target_parts[src_component].part_def
        dst_part = target_parts[dst_component].part_def
        if src_part is None or dst_part is None:
            raise ValueError("Could not resolve part definition for at least one SSD connection endpoint")
        if src_port not in src_part.ports:
            raise ValueError(f"Unknown source port '{src_component}.{src_port}' in SSD")
        if dst_port not in dst_part.ports:
            raise ValueError(f"Unknown destination port '{dst_component}.{dst_port}' in SSD")

        src_port_def = src_part.ports[src_port].port_def
        dst_port_def = dst_part.ports[dst_port].port_def
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


def _replace_system_parts(system, target_parts: Mapping[str, object]) -> None:
    system.references["parts"] = dict(target_parts)
    if hasattr(system, "declared_items"):
        system.declared_items["parts"] = dict(target_parts)


def _replace_system_connections(
    system,
    target_parts: Mapping[str, object],
    target_connections: Iterable[Tuple[str, str, str, str]],
) -> None:
    from pycps_sysmlv2 import SysMLConnection

    previous = system.references.setdefault("connections", {})
    updated = {}
    for src_component, src_port, dst_component, dst_port in sorted(target_connections):
        key = _connection_key(src_component, src_port, dst_component, dst_port)
        existing = previous.get(key)
        if existing is not None:
            updated[key] = existing
            continue
        updated[key] = SysMLConnection(
            src_component=src_component,
            src_port=src_port,
            dst_component=dst_component,
            dst_port=dst_port,
            src_part_def=target_parts[src_component].part_def,
            dst_part_def=target_parts[dst_component].part_def,
            src_port_def=target_parts[src_component].part_def.ports[src_port].port_def,
            dst_port_def=target_parts[dst_component].part_def.ports[dst_port].port_def,
        )

    system.references["connections"] = updated
    if hasattr(system, "declared_items"):
        system.declared_items["connections"] = dict(updated)


def sync_sysml_from_ssd(
    architecture_path: Path,
    ssd_path: Path,
    composition: str,
    output_architecture_dir: Path | None = None,
) -> list[Path]:
    """Apply SSD composition edits to a SysML architecture and write updated .sysml files."""
    architecture = _load_architecture(architecture_path)
    ssd_system = _load_ssd_system(ssd_path)
    system = architecture.get_part(composition)
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
