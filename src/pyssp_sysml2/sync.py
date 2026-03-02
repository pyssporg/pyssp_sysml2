"""Sync helpers to apply SSD connection changes back into SysML."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Tuple

from pyssp_standard.ssd import SSD

from pyssp_sysml2.paths import ensure_parent_dir


def _load_architecture(architecture_path: Path):
    try:
        from pycps_sysmlv2 import SysMLParser
    except ImportError as exc:  # pragma: no cover - dependency contract
        raise RuntimeError("pycps_sysmlv2 must provide SysMLParser for sync support") from exc
    return SysMLParser(architecture_path).parse()


def _split_connector(name: str) -> tuple[str, str]:
    if "." not in name:
        raise ValueError(f"Connector '{name}' is not in 'port.attribute' form")
    return name.split(".", 1)


def _derive_port_connections_from_ssd(system, ssd_path: Path) -> set[Tuple[str, str, str, str]]:
    with SSD(ssd_path, mode="r") as ssd:
        if ssd.system is None:
            raise ValueError(f"No system element found in SSD: {ssd_path}")
        ssd_connections = ssd.system.connections

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
        if src_component not in system.parts:
            raise ValueError(f"SSD references unknown source component '{src_component}'")
        if dst_component not in system.parts:
            raise ValueError(f"SSD references unknown destination component '{dst_component}'")

        src_part = system.parts[src_component].part_def
        dst_part = system.parts[dst_component].part_def
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


def _replace_system_connections(system, target_connections: Iterable[Tuple[str, str, str, str]]) -> None:
    from pycps_sysmlv2 import SysMLConnection

    previous = system.items.setdefault("connections", {})
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
            src_part_def=system.parts[src_component].part_def,
            dst_part_def=system.parts[dst_component].part_def,
            src_port_def=system.parts[src_component].part_def.ports[src_port].port_def,
            dst_port_def=system.parts[dst_component].part_def.ports[dst_port].port_def,
        )

    system.items["connections"] = updated
    if hasattr(system, "declared_items"):
        system.declared_items["connections"] = dict(updated)


def sync_sysml_from_ssd(
    architecture_path: Path,
    ssd_path: Path,
    composition: str,
    output_architecture_dir: Path | None = None,
) -> list[Path]:
    """Apply SSD connection edits to a SysML architecture and write updated .sysml files."""
    architecture = _load_architecture(architecture_path)
    system = architecture.get_part(composition)
    target_connections = _derive_port_connections_from_ssd(system, ssd_path)
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
