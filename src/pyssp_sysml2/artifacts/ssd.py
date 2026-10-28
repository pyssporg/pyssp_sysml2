"""Generic SSD generation helpers."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from pyssp_standard import (
    Component,
    ParameterBinding,
    SSD,
    SSM,
    System,
)

from pyssp_sysml2.core.control import is_control_attribute
from pyssp_sysml2.core.fmi_helpers import to_fmi_direction_definition
from pyssp_sysml2.metadata.fmu_metadata import (
    component_implementation,
    component_source,
    fmu_metadata,
)
from pyssp_sysml2.parameters.dialect.composition import (
    MappingSpec,
    has_parameter_dialect,
    validate_parameter_dialect,
)
from pyssp_sysml2.parameters.dialect.declarations import (
    parameter_declarations,
    parameter_interface,
    parameter_items,
)
from pyssp_sysml2.parameters.dialect.mapping import mapping_specs
from pyssp_sysml2.parameters.dialect.markers import (
    is_parameter_interface,
    parameter_set_resource,
)
from pyssp_sysml2.core.paths import ensure_parent_dir
from pyssp_sysml2.metadata.roles import (
    is_study,
    require_resolved_variation,
    validate_role_markers,
)
from pyssp_sysml2.metadata.ssp_metadata import ssp_metadata
from pyssp_sysml2.sysml.generate import (
    DEFAULT_START_ATTR,
    DEFAULT_STOP_ATTR,
    FLAT_CONNECTOR_ATTR,
)
from pyssp_sysml2.model import Architecture, PartDefinition, load
from pyssp_sysml2.parameters.variation import (
    require_resolved_attribute_variation,
    resolve,
)


def _endpoint_port_def(
    system: PartDefinition,
    architecture: Architecture,
    part_name: str | None,
    port_name: str,
):
    """Resolve a connection endpoint to its port definition.

    ``part_name is None`` is a port of the enclosing system itself, i.e. the
    system boundary; the SSD connection omits the element for that end.
    """
    if part_name is None:
        port_usage = system.ports.get(port_name)
        if port_usage is None:
            raise ValueError(
                f"Unknown boundary port '{port_name}' in connection; declare "
                f"it as a port of '{system.name}'"
            )
        port_def = architecture.resolve_port(port_usage)
        if port_def is None:
            raise ValueError("Port definition not connected")
        if is_parameter_interface(port_def):
            raise ValueError(
                f"Parameter port '{port_name}' cannot be connected; "
                "apply a parameter set with 'bind'"
            )
        return port_def

    part_usage = system.parts.get(part_name)
    if part_usage is None:
        raise ValueError(f"Unknown part '{part_name}' in connection")
    part_def = architecture.resolve_part(part_usage)
    if part_def is None:
        raise ValueError(f"Unresolved part definition for {part_name}")
    port_usage = part_def.ports.get(port_name)
    if port_usage is None:
        raise ValueError(f"Unknown port '{part_name}.{port_name}' in connection")
    port_def = architecture.resolve_port(port_usage)
    if port_def is None:
        raise ValueError("Port definition not connected")
    if is_parameter_interface(port_def):
        raise ValueError(
            f"Parameter port '{part_name}.{port_name}' cannot be connected; "
            "apply a parameter set with 'bind'"
        )
    return port_def


def _check_boundary_direction(
    system: PartDefinition,
    part_name: str | None,
    port_name: str,
    expected_direction: str,
) -> None:
    """A boundary endpoint must be an input at the start and an output at the end.

    Inside a system, an input port receives from the parent and feeds the
    enclosed components; an output port consumes from the enclosed components
    and exposes the value to the parent.
    """
    if part_name is not None:
        return
    port_usage = system.ports[port_name]
    if port_usage.direction != expected_direction:
        side = "start" if expected_direction == "in" else "end"
        raise ValueError(
            f"Boundary port '{port_name}' of '{system.name}' is declared as "
            f"'{port_usage.direction}' but is used as the {side} of a "
            "connection; boundary ports are inputs at the start and outputs "
            "at the end"
        )


def _parameter_binding(
    system: System, spec: MappingSpec, parameter_set_prefix: str
) -> ParameterBinding:
    """Attach one parameter binding to *system* and return it."""
    source = parameter_set_resource(parameter_set_prefix, spec.set_name)
    if spec.identity:
        return system.add_parameter_binding(
            source, prefix=f"{spec.component_name}."
        )
    return system.add_parameter_binding(
        source, mapping=SSM.create_mapping(spec.entries)
    )


def _add_part_connectors(
    element: Component | System,
    part_def: PartDefinition,
    architecture: Architecture,
    parameter_model: bool,
) -> None:
    """Append port and parameter connectors for one component or system."""
    for port_usage in part_def.ports.values():
        port_def = architecture.resolve_port(port_usage)
        if port_def is None:
            raise ValueError(
                f"Unresolved port definition for "
                f"{part_def.name}.{port_usage.name}"
            )
        if is_parameter_interface(port_def):
            # Emitted by the parameter branch below, flattened to member names.
            continue
        flat = bool(port_def.attributes.get(FLAT_CONNECTOR_ATTR))
        for attribute in port_def.attributes.values():
            if is_control_attribute(attribute.name):
                continue
            connector_name = (
                port_usage.name
                if flat
                else f"{port_usage.name}.{attribute.name}"
            )
            element.add_connector(
                name=connector_name,
                kind=to_fmi_direction_definition(port_usage.direction),
                type_name=attribute.effective_type_name,
            )

    has_interface = parameter_interface(architecture, part_def) is not None
    if parameter_model and has_interface:
        for attribute in parameter_declarations(architecture, part_def):
            for item in parameter_items(attribute):
                element.add_connector(
                    name=item.name,
                    kind="parameter",
                    type_name=item.type_name,
                )


def _add_connections(
    target_system: System,
    part_def: PartDefinition,
    architecture: Architecture,
    type_check: bool,
) -> None:
    """Append this system level's connections to an SSD system."""
    for conn in part_def.connections.values():
        if conn.source_part is None and conn.destination_part is None:
            raise ValueError(
                f"Connection '{conn.key}' links two boundary ports of "
                f"'{part_def.name}'; a connection must cross into a subpart"
            )
        src_port_def = _endpoint_port_def(
            part_def, architecture, conn.source_part, conn.source_port
        )
        dst_port_def = _endpoint_port_def(
            part_def, architecture, conn.destination_part, conn.destination_port
        )
        _check_boundary_direction(part_def, conn.source_part, conn.source_port, "in")
        _check_boundary_direction(
            part_def, conn.destination_part, conn.destination_port, "out"
        )
        if type_check and src_port_def is not dst_port_def:
            raise ValueError(
                f"Src {conn.source_port} and dest port "
                f"{conn.destination_port} must be same type"
            )

        src_flat = bool(src_port_def.attributes.get(FLAT_CONNECTOR_ATTR))
        dst_flat = bool(dst_port_def.attributes.get(FLAT_CONNECTOR_ATTR))
        for attribute_name in src_port_def.attributes.keys():
            if is_control_attribute(attribute_name):
                continue
            target_system.add_connection(
                start_element=conn.source_part,
                start_connector=(
                    conn.source_port
                    if src_flat
                    else f"{conn.source_port}.{attribute_name}"
                ),
                end_element=conn.destination_part,
                end_connector=(
                    conn.destination_port
                    if dst_flat
                    else f"{conn.destination_port}.{attribute_name}"
                ),
            )


def _write_elements(
    parent: System,
    part_def: PartDefinition,
    architecture: Architecture,
    *,
    parameter_model: bool,
    type_check: bool,
) -> None:
    """Recursively write nested systems and leaf FMU components."""
    for part_name, part_usage in part_def.parts.items():
        child = architecture.resolve_part(part_usage)
        if child is None:
            raise ValueError(
                f"Unresolved part definition for {part_usage.name}"
            )
        metadata = fmu_metadata(architecture, child)
        if child.parts:
            if metadata is not None:
                raise ValueError(
                    f"{child.name} has both subparts and 'fmu_meta' metadata; "
                    "a nested system cannot also be an FMU component"
                )
            nested = parent.add_subsystem(part_name)
            _add_part_connectors(nested, child, architecture, parameter_model)
            _write_elements(
                nested,
                child,
                architecture,
                parameter_model=parameter_model,
                type_check=type_check,
            )
            continue

        component = parent.add_component(
            part_name,
            source=component_source(child, metadata),
            component_type="application/x-fmu-sharedlibrary",
            implementation=component_implementation(metadata),
        )
        _add_part_connectors(component, child, architecture, parameter_model)

    _add_connections(parent, part_def, architecture, type_check)


def build_ssd(
    ssd: SSD,
    system: PartDefinition,
    architecture: Architecture,
    type_check=True,
    parameter_set_prefix: str = "parameter_sets",
) -> None:
    validate_role_markers(architecture)
    if is_study(architecture, system):
        raise ValueError(
            f"Composition '{system.name}' is a Study; studies generate scenario "
            "data and are never exported as an SSD or SSP"
        )
    if ssp_metadata(architecture, system) is not None:
        raise ValueError(
            f"Composition '{system.name}' selects an external SSP source via "
            "'ssp_meta'; it is a study-only boundary and cannot be exported"
        )
    top = ssd.new_system(system.name)
    ssd.rename(system.name)

    if parameter_interface(architecture, system) is not None:
        raise ValueError(
            "Top-level composition parameter interfaces are not supported; "
            "attach parameter interfaces to component usages"
        )

    validate_parameter_dialect(architecture, system)
    parameter_model = has_parameter_dialect(architecture, system)
    specs = mapping_specs(architecture, system) if parameter_model else []

    _add_part_connectors(top, system, architecture, parameter_model)
    _write_elements(
        top,
        system,
        architecture,
        parameter_model=parameter_model,
        type_check=type_check,
    )

    start = system.attributes.get(DEFAULT_START_ATTR)
    stop = system.attributes.get(DEFAULT_STOP_ATTR)
    ssd.set_default_experiment(
        start_time=float(start.value) if start is not None else 0,
        stop_time=float(stop.value) if stop is not None else 3600,
    )

    if parameter_model:
        for spec in specs:
            _parameter_binding(top, spec, parameter_set_prefix)


def generate_ssd(
    architecture_path: Path,
    output_path: Path,
    composition: str,
    type_check=True,
    parameter_set_prefix: str = "parameter_sets",
    selections: Mapping[str, str] | None = None,
) -> Path:

    architecture = load(architecture_path)
    system = architecture.get_part_def(composition)
    if selections:
        architecture = resolve(architecture, system, selections)
        system = architecture.get_part_def(composition)
    require_resolved_variation(architecture, system)
    require_resolved_attribute_variation(architecture, system)
    ensure_parent_dir(output_path)
    with SSD(output_path, mode="w") as ssd:
        build_ssd(
            ssd,
            system,
            architecture,
            type_check,
            parameter_set_prefix=parameter_set_prefix,
        )
    return output_path
