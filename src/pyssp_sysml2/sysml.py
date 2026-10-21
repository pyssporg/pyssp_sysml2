"""Helpers for generating minimal SysML models from SSD files."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable

from pyssp_standard.ssd import Component, SSD
from pyssp_standard.ssv import SSV

from pyssp_sysml2.paths import ensure_parent_dir, DEFAULT_PACKAGE_NAME
from pyssp_sysml2.sysml_model import (
    Architecture,
    Attribute,
    Connection,
    PartDefinition,
    PartUsage,
    PortDefinition,
    PortUsage,
)

SCALAR_ATTRIBUTE_NAME = "value"

# Control attributes carry SSD metadata that SysML v2 has no first-class
# equivalent for. They are written as ordinary attributes so the exporter and
# loader preserve them, and every generator skips them as model data.
CONTROL_PREFIX = "pyssp_"
IMPLEMENTATION_ATTR = f"{CONTROL_PREFIX}implementation"
PARAMETER_SET_ATTR = f"{CONTROL_PREFIX}parameter_set"
DEFAULT_START_ATTR = f"{CONTROL_PREFIX}default_start_time"
DEFAULT_STOP_ATTR = f"{CONTROL_PREFIX}default_stop_time"
FLAT_CONNECTOR_ATTR = f"{CONTROL_PREFIX}flat_connector"


def is_control_attribute(name: str) -> bool:
    return name.startswith(CONTROL_PREFIX)


def load_ssd_system(ssd_path: Path):
    if not Path(ssd_path).is_file():
        raise FileNotFoundError(f"SSD file not found: {ssd_path}")
    with SSD(ssd_path, mode="r") as ssd:
        if ssd.xml.system is None:
            raise ValueError(f"No system element found in SSD: {ssd_path}")
        return ssd.xml.system


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


def _coerce_parameter_value(type_name: str, value: object) -> object:
    if value is None:
        return None
    if type_name == "Real":
        return float(value)
    if type_name == "Integer":
        return int(value)
    if type_name == "Boolean":
        return str(value).lower() == "true"
    return str(value)


def _parameter_values(ssd_path: Path | None, bindings) -> dict[str, tuple[str, object]]:
    """Collect parameter name -> (type, value) from SSD/SSV bindings."""
    values: dict[str, tuple[str, object]] = {}

    def collect(parameters) -> None:
        for name, type_name, raw in parameters:
            values[name] = (type_name, _coerce_parameter_value(type_name, raw))

    def from_parameter_set(parameter_set) -> list[tuple[str, str, object]]:
        return [
            (parameter.name, parameter.type_name, parameter.attributes.get("value"))
            for parameter in parameter_set.parameters
        ]

    for binding in bindings or []:
        inline = getattr(binding, "parameter_set", None)
        if inline is not None:
            collect(from_parameter_set(inline))
            continue
        source = getattr(binding, "source", None)
        if ssd_path is None or not source:
            continue
        source_path = (ssd_path.parent / source).resolve()
        if source_path.is_file():
            with SSV(source_path, mode="r") as ssv:
                collect(from_parameter_set(ssv.xml))
    return values


def _control_attribute(name: str, value: object, type_name: str) -> Attribute:
    return Attribute(name=name, type_name=type_name, value=value)


def build_architecture_from_ssd(
    ssd_system,
    composition: str,
    *,
    ssd_path: Path | None = None,
    default_experiment=None,
):
    components = index_components(ssd_system)
    parameter_values = _parameter_values(
        ssd_path, getattr(ssd_system, "parameter_bindings", None)
    )
    endpoint_attributes: dict[tuple[str, str], dict[str, str]] = {}
    endpoint_directions: dict[tuple[str, str], str] = {}
    flat_endpoints: set[tuple[str, str]] = set()

    for component in components.values():
        for connector in component.connectors:
            if connector.kind == "parameter":
                continue
            port_name, attribute_name = split_connector_or_scalar(connector.name)
            endpoint = (component.name, port_name)
            if "." not in connector.name:
                flat_endpoints.add(endpoint)
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
    flat_groups = {
        endpoint_groups[endpoint]
        for endpoint in flat_endpoints
        if endpoint in endpoint_groups
    }

    architecture = Architecture(package_name=DEFAULT_PACKAGE_NAME)
    part_defs_by_name: dict[str, PartDefinition] = {}
    component_part_defs: dict[str, PartDefinition] = {}
    port_defs_by_signature: dict[tuple[tuple[str, str], ...], PortDefinition] = {}

    for component_name in sorted(components):
        component = components[component_name]
        part_name = _part_name_from_component(component)
        part_def = part_defs_by_name.get(part_name)
        if part_def is None:
            part_def = PartDefinition(name=part_name, source_file="architecture.sysml")
            architecture.add_part_def(part_def)
            part_defs_by_name[part_name] = part_def
        component_part_defs[component_name] = part_def

        if getattr(component, "implementation", None):
            part_def.attributes[IMPLEMENTATION_ATTR] = _control_attribute(
                IMPLEMENTATION_ATTR, component.implementation, "String"
            )

        for connector in component.connectors:
            if connector.kind != "parameter":
                continue
            type_name = _type_name_from_connector(connector)
            _, value = parameter_values.get(
                f"{component_name}.{connector.name}", (type_name, None)
            )
            part_def.attributes[connector.name] = Attribute(
                name=connector.name,
                type_name=type_name,
                value=value,
            )

        for endpoint in sorted(key for key in endpoint_attributes if key[0] == component_name):
            _, port_name = endpoint
            signature = group_signatures[endpoint_groups[endpoint]]
            port_def = port_defs_by_signature.get(signature)
            if port_def is None:
                port_def_name = f"Port_{len(port_defs_by_signature) + 1}"
                port_def = PortDefinition(name=port_def_name, source_file="architecture.sysml")
                for attr_name, attr_type in signature:
                    port_def.attributes[attr_name] = Attribute(
                        name=attr_name,
                        type_name=attr_type,
                        value=None,
                    )
                if endpoint_groups[endpoint] in flat_groups:
                    port_def.attributes[FLAT_CONNECTOR_ATTR] = _control_attribute(
                        FLAT_CONNECTOR_ATTR, True, "Boolean"
                    )
                architecture.add_port_def(port_def)
                port_defs_by_signature[signature] = port_def

            if port_name not in part_def.ports:
                part_def.ports[port_name] = PortUsage(
                    name=port_name,
                    direction=endpoint_directions.get(endpoint, "in"),
                    type_name=port_def.name,
                )

    system = PartDefinition(name=composition, source_file="architecture.sysml")
    architecture.add_part_def(system)
    for binding in getattr(ssd_system, "parameter_bindings", None) or []:
        if getattr(binding, "source", None):
            system.attributes[PARAMETER_SET_ATTR] = _control_attribute(
                PARAMETER_SET_ATTR, binding.source, "String"
            )
            break
    if default_experiment is not None:
        system.attributes[DEFAULT_START_ATTR] = _control_attribute(
            DEFAULT_START_ATTR, default_experiment.start_time, "Real"
        )
        system.attributes[DEFAULT_STOP_ATTR] = _control_attribute(
            DEFAULT_STOP_ATTR, default_experiment.stop_time, "Real"
        )
    for component_name in sorted(components):
        part_def = component_part_defs[component_name]
        system.parts[component_name] = PartUsage(
            name=component_name,
            type_name=part_def.name,
        )

    grouped: Dict[tuple[str, str, str, str], set[str]] = {}
    for connection in ssd_system.connections:
        src_port, src_attr = split_connector_or_scalar(connection.start_connector)
        dst_port, _ = split_connector_or_scalar(connection.end_connector)
        key = (connection.start_element, src_port, connection.end_element, dst_port)
        grouped.setdefault(key, set()).add(src_attr)

    for src_component, src_port, dst_component, dst_port in sorted(grouped):
        connection = Connection(
            name=f"{src_component}.{src_port}_to_{dst_component}.{dst_port}",
            source_part=src_component,
            source_port=src_port,
            destination_part=dst_component,
            destination_port=dst_port,
        )
        system.connections[connection.key] = connection

    return architecture, system


def generate_sysml_from_ssd(
    ssd_path: Path,
    output_path: Path,
    composition: str | None = None,
) -> Path:
    with SSD(ssd_path, mode="r") as ssd:
        ssd_system = ssd.xml.system
        if ssd_system is None:
            raise ValueError(f"No system element found in SSD: {ssd_path}")
        composition_name = composition or ssd_system.name
        if not composition_name:
            raise ValueError("Composition name must be provided or present on the SSD system")
        architecture, _ = build_architecture_from_ssd(
            ssd_system,
            composition_name,
            ssd_path=ssd_path,
            default_experiment=ssd.xml.default_experiment,
        )
    file_texts = architecture.export_declared()
    if len(file_texts) != 1:
        raise ValueError("SSD-to-SysML generation expected a single exported architecture file")

    content = next(iter(file_texts.values()))
    ensure_parent_dir(output_path)
    output_path.write_text(content, encoding="utf-8")
    return output_path
