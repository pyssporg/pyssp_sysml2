"""Helpers for generating minimal SysML models from SSD files."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pyssp_standard import Component, SSD, System

from pyssp_sysml2.control import (
    DEFAULT_START_ATTR,
    DEFAULT_STOP_ATTR,
    FLAT_CONNECTOR_ATTR,
    is_control_attribute,
)
from pyssp_sysml2.fmu_metadata import update_fmu_metadata_from_component
from pyssp_sysml2.parameter_synthesis import synthesize_parameter_dialect
from pyssp_sysml2.parameters import is_parameter_interface
from pyssp_sysml2.paths import ensure_parent_dir, DEFAULT_PACKAGE_NAME
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
from pyssp_sysml2.variation import refuse_variation_erasure

SCALAR_ATTRIBUTE_NAME = "value"


def load_ssd_system(ssd_path: Path):
    if not Path(ssd_path).is_file():
        raise FileNotFoundError(f"SSD file not found: {ssd_path}")
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


def _type_name_from_connector(connector) -> str:
    type_name = connector.type_name or "Real"
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


def _part_name_from_component(component: Component) -> str:
    if component.source:
        return Path(component.source).stem
    if component.name:
        return component.name
    raise ValueError("SSD component without a name cannot be synced")


def _control_attribute(name: str, value: object, type_name: str) -> Attribute:
    return Attribute(name=name, type_name=type_name, value=value)


def _port_connector_groups(element) -> dict[str, list[tuple[str, object]]]:
    grouped: dict[str, list[tuple[str, object]]] = {}
    for connector in element.connectors:
        if connector.kind == "parameter":
            continue
        port_name, attribute_name = split_connector_or_scalar(connector.name)
        grouped.setdefault(port_name, []).append((attribute_name, connector))
    return grouped


def _port_signature_from_connectors(
    connectors: list[tuple[str, object]],
) -> tuple[tuple[tuple[str, str], ...], bool]:
    attrs: dict[str, str] = {}
    flat = False
    for attribute_name, connector in connectors:
        if "." not in connector.name:
            flat = True
        attr_type = _type_name_from_connector(connector)
        previous = attrs.get(attribute_name)
        attrs[attribute_name] = (
            attr_type
            if previous is None
            else _merge_type_names([previous, attr_type])
        )
    is_scalar = len(attrs) <= 1
    canonical = {
        SCALAR_ATTRIBUTE_NAME if is_scalar else name: attr_type
        for name, attr_type in attrs.items()
    }
    return tuple(sorted(canonical.items())), flat


def _port_def_signature(
    port_def: PortDefinition,
) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (attribute.name, attribute.effective_type_name)
            for attribute in port_def.attributes.values()
            if not is_control_attribute(attribute.name)
        )
    )


def _port_def_for(
    architecture: Architecture,
    cache: dict[tuple[tuple[tuple[str, str], ...], bool], PortDefinition],
    signature: tuple[tuple[str, str], ...],
    flat: bool,
    *,
    source_file: str = "architecture.sysml",
) -> PortDefinition:
    key = (signature, flat)
    port_def = cache.get(key)
    if port_def is not None:
        return port_def
    for existing in architecture.port_definitions.values():
        if is_parameter_interface(existing):
            continue
        if (
            _port_def_signature(existing) == signature
            and bool(existing.attributes.get(FLAT_CONNECTOR_ATTR)) == flat
        ):
            cache[key] = existing
            return existing

    port_def = PortDefinition(
        name=f"Port_{len(architecture.port_definitions) + 1}",
        source_file=source_file,
    )
    for attribute_name, attribute_type in signature:
        port_def.attributes[attribute_name] = Attribute(
            name=attribute_name,
            type_name=attribute_type,
            value=None,
        )
    if flat:
        port_def.attributes[FLAT_CONNECTOR_ATTR] = _control_attribute(
            FLAT_CONNECTOR_ATTR, True, "Boolean"
        )
    architecture.add_port_def(port_def)
    cache[key] = port_def
    return port_def


def _ensure_ports_for_element(
    part_def: PartDefinition,
    element,
    architecture: Architecture,
    cache: dict[tuple[tuple[tuple[str, str], ...], bool], PortDefinition],
    *,
    source_file: str = "architecture.sysml",
) -> None:
    for port_name, connectors in sorted(_port_connector_groups(element).items()):
        signature, flat = _port_signature_from_connectors(connectors)
        port_def = _port_def_for(
            architecture, cache, signature, flat, source_file=source_file
        )
        direction = (
            "out"
            if any(connector.kind == "output" for _, connector in connectors)
            else "in"
        )
        existing = part_def.ports.get(port_name)
        if existing is not None:
            if existing.type_name != port_def.name:
                raise ValueError(
                    f"{part_def.name}.{port_name} is declared with conflicting "
                    "port types"
                )
            continue
        part_def.ports[port_name] = PortUsage(
            name=port_name,
            direction=direction,
            type_name=port_def.name,
        )


def _unique_part_def_name(architecture: Architecture, base: str) -> str:
    candidate = base or "Part"
    counter = 2
    while candidate in architecture.part_definitions:
        candidate = f"{base}_{counter}"
        counter += 1
    return candidate


def _ensure_component_part_def(
    architecture: Architecture,
    component: Component,
    component_defs: dict[str, PartDefinition],
    port_cache: dict[tuple[tuple[tuple[str, str], ...], bool], PortDefinition],
) -> PartDefinition:
    base_name = _part_name_from_component(component)
    part_def = component_defs.get(base_name)
    if part_def is None:
        part_name = (
            base_name
            if base_name not in architecture.part_definitions
            else _unique_part_def_name(architecture, base_name)
        )
        part_def = PartDefinition(name=part_name, source_file="architecture.sysml")
        architecture.add_part_def(part_def)
        component_defs[base_name] = part_def

    update_fmu_metadata_from_component(
        architecture,
        part_def,
        component,
        source_file="architecture.sysml",
    )
    _ensure_ports_for_element(part_def, component, architecture, port_cache)
    return part_def


def _ensure_system_part_def(
    architecture: Architecture,
    system_element,
    port_cache: dict[tuple[tuple[tuple[str, str], ...], bool], PortDefinition],
    *,
    source_file: str = "architecture.sysml",
) -> PartDefinition:
    base_name = system_element.name or "System"
    part_name = (
        base_name
        if base_name not in architecture.part_definitions
        else _unique_part_def_name(architecture, base_name)
    )
    part_def = PartDefinition(name=part_name, source_file=source_file)
    architecture.add_part_def(part_def)
    _ensure_ports_for_element(
        part_def,
        system_element,
        architecture,
        port_cache,
        source_file=source_file,
    )
    return part_def


def _connection_endpoint_port_def(
    system: PartDefinition,
    architecture: Architecture,
    child_elements: dict[str, Component | System],
    element_name: str | None,
    port_name: str,
    connection_text: str,
) -> PortDefinition:
    """Resolve one SSD connection endpoint to its port definition.

    ``element_name is None`` is a connector of the enclosing system itself,
    i.e. the system boundary.
    """
    if element_name is None:
        port_usage = system.ports.get(port_name)
        if port_usage is None:
            raise ValueError(
                "SSD connection references a boundary port that is not "
                f"declared by the system connectors: {connection_text}"
            )
    else:
        if element_name not in child_elements:
            raise ValueError(
                f"SSD connection references unknown element '{element_name}'"
            )
        part_usage = system.parts.get(element_name)
        if part_usage is None:
            raise ValueError("SSD connection endpoint has no part usage")
        part_def = architecture.resolve_part(part_usage)
        if part_def is None:
            raise ValueError("Could not resolve SSD connection endpoint")
        port_usage = part_def.ports.get(port_name)
        if port_usage is None:
            raise ValueError(
                "SSD connection references a port that is not declared by "
                f"its element connectors: {connection_text}"
            )

    port_def = architecture.resolve_port(port_usage)
    if port_def is None:
        raise ValueError("Could not resolve SSD connection port")
    return port_def


def _connection_sort_key(
    item: tuple[str | None, str, str | None, str],
) -> tuple[str, str, str, str]:
    """Order connections, sorting boundary ends (``None``) first."""
    return tuple("" if value is None else value for value in item)


def _add_level_connections(
    part_def: PartDefinition,
    ssd_system,
    child_elements: dict[str, Component | System],
    architecture: Architecture,
) -> None:
    grouped: dict[tuple[str | None, str, str | None, str], set[str]] = {}
    for connection in ssd_system.connections:
        src_port, src_attribute = split_connector_or_scalar(
            connection.start_connector
        )
        dst_port, _ = split_connector_or_scalar(connection.end_connector)
        key = (
            connection.start_element,
            src_port,
            connection.end_element,
            dst_port,
        )
        grouped.setdefault(key, set()).add(src_attribute)

    for src_element, src_port, dst_element, dst_port in sorted(
        grouped, key=_connection_sort_key
    ):
        connection_text = (
            f"{endpoint_text(src_element, src_port)} -> "
            f"{endpoint_text(dst_element, dst_port)}"
        )
        src_port_def = _connection_endpoint_port_def(
            part_def, architecture, child_elements, src_element, src_port,
            connection_text,
        )
        dst_port_def = _connection_endpoint_port_def(
            part_def, architecture, child_elements, dst_element, dst_port,
            connection_text,
        )
        if src_port_def is not dst_port_def:
            raise ValueError(
                f"SSD connects incompatible ports: {connection_text}"
            )
        connection = Connection(
            name=(
                f"{endpoint_text(src_element, src_port)}"
                f"_to_{endpoint_text(dst_element, dst_port)}"
            ),
            source_part=src_element,
            source_port=src_port,
            destination_part=dst_element,
            destination_port=dst_port,
        )
        part_def.connections[connection.key] = connection


def _build_system_children(
    part_def: PartDefinition,
    ssd_system,
    architecture: Architecture,
    component_defs: dict[str, PartDefinition],
    port_cache: dict[tuple[tuple[tuple[str, str], ...], bool], PortDefinition],
) -> None:
    child_elements: dict[str, Component | System] = {}
    for element in sorted(
        ssd_system.elements, key=lambda item: item.name or ""
    ):
        if not element.name:
            raise ValueError("SSD element without a name cannot be synced")
        if element.name in child_elements:
            raise ValueError(
                f"SSD contains duplicate element '{element.name}'"
            )
        child_elements[element.name] = element

        if isinstance(element, Component):
            child_def = _ensure_component_part_def(
                architecture, element, component_defs, port_cache
            )
        elif isinstance(element, System):
            child_def = _ensure_system_part_def(
                architecture, element, port_cache
            )
        else:
            raise ValueError(
                f"Unsupported SSD element type: {type(element).__name__}"
            )

        part_def.parts[element.name] = PartUsage(
            name=element.name,
            type_name=child_def.name,
        )
        if isinstance(element, System):
            _build_system_children(
                child_def,
                element,
                architecture,
                component_defs,
                port_cache,
            )

    _add_level_connections(
        part_def, ssd_system, child_elements, architecture
    )


def build_architecture_from_ssd(
    ssd_system,
    composition: str,
    *,
    ssd_path: Path | None = None,
    default_experiment=None,
):
    architecture = Architecture(package_name=DEFAULT_PACKAGE_NAME)
    port_cache: dict[
        tuple[tuple[tuple[str, str], ...], bool], PortDefinition
    ] = {}

    system = PartDefinition(name=composition, source_file="architecture.sysml")
    architecture.add_part_def(system)
    _ensure_ports_for_element(system, ssd_system, architecture, port_cache)
    if default_experiment is not None:
        system.attributes[DEFAULT_START_ATTR] = _control_attribute(
            DEFAULT_START_ATTR, default_experiment.start_time, "Real"
        )
        system.attributes[DEFAULT_STOP_ATTR] = _control_attribute(
            DEFAULT_STOP_ATTR, default_experiment.stop_time, "Real"
        )

    component_defs: dict[str, PartDefinition] = {}
    _build_system_children(
        system,
        ssd_system,
        architecture,
        component_defs,
        port_cache,
    )

    synthesize_parameter_dialect(
        architecture,
        system,
        ssd_system,
        ssd_path,
        source_file="architecture.sysml",
    )

    return architecture, system


def generate_sysml_from_ssd(
    ssd_path: Path,
    output_path: Path,
    composition: str | None = None,
) -> Path:
    if output_path.suffix == ".sysml" and output_path.is_file():
        refuse_variation_erasure(load(output_path), output_path)
    with SSD(ssd_path, mode="r") as ssd:
        ssd_system = ssd.system
        if ssd_system is None:
            raise ValueError(f"No system element found in SSD: {ssd_path}")
        composition_name = composition or ssd_system.name
        if not composition_name:
            raise ValueError("Composition name must be provided or present on the SSD system")
        architecture, _ = build_architecture_from_ssd(
            ssd_system,
            composition_name,
            ssd_path=ssd_path,
            default_experiment=ssd.default_experiment,
        )
    file_texts = architecture.export_declared()
    if len(file_texts) != 1:
        raise ValueError("SSD-to-SysML generation expected a single exported architecture file")

    content = next(iter(file_texts.values()))
    ensure_parent_dir(output_path)
    output_path.write_text(content, encoding="utf-8")
    return output_path
