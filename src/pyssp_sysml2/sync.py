"""Sync helpers to apply SSD composition changes back into SysML."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Mapping, Tuple

from pyssp_standard.ssd import Component, System

from pyssp_sysml2.fmu_metadata import (
    component_source,
    fmu_metadata,
    update_fmu_metadata_from_component,
)
from pyssp_sysml2.parameter_synthesis import synthesize_parameter_dialect
from pyssp_sysml2.parameters import (
    has_parameter_dialect,
    validate_parameter_dialect,
)
from pyssp_sysml2.paths import ensure_parent_dir
from pyssp_sysml2.sysml import (
    SCALAR_ATTRIBUTE_NAME,
    _ensure_system_part_def,
    _merge_type_names,
    _part_name_from_component,
    _type_name_from_connector,
    build_architecture_from_ssd,
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
    endpoint_text,
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
    update_fmu_metadata_from_component(
        architecture,
        part_def,
        component,
        source_file=INFERRED_PARTS_FILENAME,
    )

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
        existing_metadata = fmu_metadata(architecture, existing_part_def)
        existing_source = component_source(existing_part_def, existing_metadata)
        # An empty SSD source, or an unauthored FMU source, places no
        # constraint on the part: match by name so its metadata is not
        # duplicated and an authored source is preserved.
        if (
            not component.source
            or component.source == existing_source
            or (existing_metadata is not None and not existing_metadata.source)
        ):
            update_fmu_metadata_from_component(
                architecture,
                existing_part_def,
                component,
                source_file=INFERRED_PARTS_FILENAME,
            )
            return existing.type_name, existing_part_def

    if not component.source:
        raise ValueError(
            f"SSD component '{component.name}' has no source, so its SysML part "
            "definition cannot be resolved"
        )

    matches = [
        part_def
        for part_def in architecture.part_definitions.values()
        if component_source(
            part_def, fmu_metadata(architecture, part_def)
        ) == component.source
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


def _resolve_system_part_definition(
    architecture: Architecture,
    part_def: PartDefinition,
    system_element,
    *,
    synthesize_external_parts: bool,
    port_cache,
):
    existing = part_def.parts.get(system_element.name)
    if existing is not None:
        existing_def = architecture.resolve_part(existing)
        if existing_def is not None:
            return existing.type_name, existing_def

    candidate = architecture.part_definitions.get(system_element.name or "")
    if candidate is not None:
        return candidate.name, candidate

    if not synthesize_external_parts:
        raise ValueError(
            f"SSD system '{system_element.name}' has no matching SysML part "
            "definition"
        )
    child_def = _ensure_system_part_def(
        architecture,
        system_element,
        port_cache,
        source_file=INFERRED_PARTS_FILENAME,
    )
    return child_def.name, child_def


def _sync_system_level(
    architecture: Architecture,
    part_def: PartDefinition,
    ssd_system,
    *,
    synthesize_external_parts: bool,
    port_cache,
) -> None:
    """Reconcile one SSD system level and recurse into nested systems."""
    target_parts: dict[str, PartUsage] = {}
    elements = sorted(
        ssd_system.elements, key=lambda item: item.name or ""
    )
    for element in elements:
        if not element.name:
            raise ValueError("SSD element without a name cannot be synced")
        if isinstance(element, Component):
            part_name, child_def = _resolve_component_part_definition(
                architecture,
                part_def,
                element,
                synthesize_external_parts=synthesize_external_parts,
            )
        elif isinstance(element, System):
            part_name, child_def = _resolve_system_part_definition(
                architecture,
                part_def,
                element,
                synthesize_external_parts=synthesize_external_parts,
                port_cache=port_cache,
            )
        else:
            raise ValueError(
                f"Unsupported SSD element type: {type(element).__name__}"
            )

        existing = part_def.parts.get(element.name)
        if (
            existing is not None
            and existing.type_name == part_name
            and architecture.resolve_part(existing) is child_def
        ):
            target_parts[element.name] = existing
        else:
            target_parts[element.name] = PartUsage(
                name=element.name,
                type_name=part_name,
                doc=getattr(existing, "doc", None),
            )

        if isinstance(element, System):
            _sync_system_level(
                architecture,
                child_def,
                element,
                synthesize_external_parts=synthesize_external_parts,
                port_cache=port_cache,
            )

    target_connections = _derive_port_connections_from_ssd(
        target_parts, part_def, ssd_system, architecture
    )
    _replace_system_parts(part_def, target_parts)
    _replace_system_connections(part_def, target_connections)


def _derive_port_connections_from_ssd(
    target_parts: Mapping[str, PartUsage],
    part_def: PartDefinition,
    ssd_system,
    architecture: Architecture,
) -> set[Tuple[str | None, str, str | None, str]]:
    grouped: Dict[Tuple[str | None, str, str | None, str], set[str]] = {}
    for conn in ssd_system.connections:
        src_port, src_attr = split_connector(conn.start_connector)
        dst_port, dst_attr = split_connector(conn.end_connector)
        if src_attr != dst_attr:
            raise ValueError(
                "SSD uses attribute remapping that cannot be represented as a SysML port connect: "
                f"{endpoint_text(conn.start_element, conn.start_connector)}"
                f" -> {endpoint_text(conn.end_element, conn.end_connector)}"
            )
        key = (conn.start_element, src_port, conn.end_element, dst_port)
        grouped.setdefault(key, set()).add(src_attr)

    target: set[Tuple[str | None, str, str | None, str]] = set()
    for src_component, src_port, dst_component, dst_port in grouped:
        connection_text = (
            f"{endpoint_text(src_component, src_port)} -> "
            f"{endpoint_text(dst_component, dst_port)}"
        )
        src_port_def = _connection_endpoint_port_def(
            target_parts,
            part_def,
            architecture,
            src_component,
            src_port,
            role="source",
            connection_text=connection_text,
        )
        dst_port_def = _connection_endpoint_port_def(
            target_parts,
            part_def,
            architecture,
            dst_component,
            dst_port,
            role="destination",
            connection_text=connection_text,
        )
        if src_port_def is not dst_port_def:
            raise ValueError(
                "SSD connects incompatible ports that cannot be represented in SysML composition: "
                f"{connection_text}"
            )

        required_attributes = set(src_port_def.attributes.keys())
        actual_attributes = grouped[(src_component, src_port, dst_component, dst_port)]
        if required_attributes != actual_attributes:
            missing = sorted(required_attributes - actual_attributes)
            extra = sorted(actual_attributes - required_attributes)
            raise ValueError(
                "SSD contains a partial/invalid attribute mapping for port connection "
                f"{connection_text}. "
                f"missing={missing}, extra={extra}"
            )

        target.add((src_component, src_port, dst_component, dst_port))

    return target


def _connection_endpoint_port_def(
    target_parts: Mapping[str, PartUsage],
    part_def: PartDefinition,
    architecture: Architecture,
    component: str | None,
    port: str,
    *,
    role: str,
    connection_text: str,
) -> PortDefinition:
    """Resolve one endpoint; a ``None`` component is a boundary port."""
    if component is None:
        port_usage = part_def.ports.get(port)
        if port_usage is None:
            raise ValueError(
                f"Unknown boundary port '{port}' in SSD connection "
                f"{connection_text}; declare it on '{part_def.name}'"
            )
    else:
        part_usage = target_parts.get(component)
        if part_usage is None:
            raise ValueError(f"SSD references unknown {role} component '{component}'")
        part = architecture.resolve_part(part_usage)
        if part is None:
            raise ValueError(
                "Could not resolve part definition for at least one SSD connection endpoint"
            )
        port_usage = part.ports.get(port)
        if port_usage is None:
            raise ValueError(f"Unknown {role} port '{component}.{port}' in SSD")

    port_def = architecture.resolve_port(port_usage)
    if port_def is None:
        raise ValueError(
            "Could not resolve port definition for at least one SSD connection endpoint"
        )
    return port_def


def _connection_sort_key(
    item: Tuple[str | None, str, str | None, str],
) -> Tuple[str, str, str, str]:
    return tuple("" if value is None else value for value in item)


def _connection_key(
    src_component: str | None,
    src_port: str,
    dst_component: str | None,
    dst_port: str,
) -> str:
    return (
        f"{endpoint_text(src_component, src_port)}"
        f"->{endpoint_text(dst_component, dst_port)}"
    )


def _replace_system_parts(system: PartDefinition, target_parts: Mapping[str, PartUsage]) -> None:
    system.parts.clear()
    system.parts.update(target_parts)


def _replace_system_connections(
    system: PartDefinition,
    target_connections: Iterable[Tuple[str | None, str, str | None, str]],
) -> None:
    previous = system.connections
    updated = {}
    for src_component, src_port, dst_component, dst_port in sorted(
        target_connections, key=_connection_sort_key
    ):
        key = _connection_key(src_component, src_port, dst_component, dst_port)
        existing = previous.get(key)
        if existing is not None:
            updated[key] = existing
            continue
        updated[key] = Connection(
            name=(
                f"{endpoint_text(src_component, src_port)}"
                f"_to_{endpoint_text(dst_component, dst_port)}"
            ),
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
    loaded = True
    try:
        architecture = _load_architecture(architecture_path)
        system = architecture.get_part_def(composition)
    except FileNotFoundError:
        architecture, system = build_architecture_from_ssd(
            ssd_system, composition, ssd_path=ssd_path
        )
        loaded = False

    if loaded:
        validate_parameter_dialect(architecture, system)
    parameter_dialect = loaded and has_parameter_dialect(architecture, system)

    _sync_system_level(
        architecture,
        system,
        ssd_system,
        synthesize_external_parts=synthesize_external_parts,
        port_cache={},
    )
    if parameter_dialect:
        synthesize_parameter_dialect(
            architecture,
            system,
            ssd_system,
            ssd_path,
            source_file="parameter_sets.sysml",
            sync=True,
        )

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
