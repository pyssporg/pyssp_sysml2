"""Generic SSD generation helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from pyssp_standard import (
    Component,
    ParameterBinding,
    SSD,
    SSM,
    System,
)

from pycps_sysml2.core.control import (
    DEFAULT_START_ATTR,
    DEFAULT_STOP_ATTR,
    FLAT_CONNECTOR_ATTR,
    is_control_attribute,
)
from pycps_sysml2.core.fmi_helpers import to_fmi_direction_definition
from pycps_sysml2.metadata.fmu_metadata import (
    component_implementation,
    component_source,
    fmu_metadata,
)
from pycps_sysml2.metadata.roles import (
    SSP_ROLES,
    is_analysis,
    require_resolved_variation,
    validate_role_markers,
)
from pycps_sysml2.metadata.ssp_metadata import ssp_metadata
from pycps_sysml2.model import (
    Architecture,
    PartDefinition,
    PortDefinition,
    PortUsage,
    load,
)
from pycps_sysml2.parameters.constraints import enforce_constraints
from pycps_sysml2.parameters.dialect.composition import (
    MappingSpec,
    has_parameter_dialect,
    validate_parameter_dialect,
)
from pycps_sysml2.parameters.dialect.declarations import (
    fixed_count,
    parameter_declarations,
    parameter_interface,
    parameter_items,
)
from pycps_sysml2.parameters.dialect.mapping import mapping_specs
from pycps_sysml2.parameters.dialect.markers import is_parameter_interface
from pycps_sysml2.parameters.policy import SSP_POLICY
from pycps_sysml2.parameters.variation import (
    require_resolved_attribute_variation,
    resolve_selected,
)

from pyssp_sysml2.artifacts.ssv import parameter_set_resource
from pyssp_sysml2.core.paths import ensure_parent_dir


def _endpoint_port_def(
    system: PartDefinition,
    architecture: Architecture,
    part_name: str | None,
    port_name: str,
):
    """Resolve a connection endpoint to its port definition and usage.

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
        return port_def, port_usage

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
    return port_def, port_usage


def _port_indices(port_usage: PortUsage) -> tuple[int | None, ...]:
    """Connector indices for one port usage; 1-based to match FMI arrays."""
    if not port_usage.multiplicity:
        return (None,)
    count = fixed_count(port_usage.multiplicity, port_usage.name)
    return tuple(range(1, count + 1))


def flat_connector(port_def: PortDefinition) -> bool:
    """True when ``port_def`` asks for flattened connectors.

    The control attribute is a Boolean; an absent attribute or ``false`` means
    per-member connectors, so the stored value must be read, never the presence
    of the attribute.
    """
    attribute = port_def.attributes.get(FLAT_CONNECTOR_ATTR)
    return attribute is not None and bool(attribute.value)


def _multiplicity_text(port_usage: PortUsage) -> str:
    return f"[{port_usage.multiplicity}]" if port_usage.multiplicity else ""


def _connector_name(
    port_usage: PortUsage,
    attribute_name: str,
    flat: bool,
    index: int | None,
) -> str:
    port = port_usage.name if index is None else f"{port_usage.name}[{index}]"
    return port if flat else f"{port}.{attribute_name}"


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
    *,
    base_index: int = 0,
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
        flat = flat_connector(port_def)
        for index in _port_indices(port_usage):
            for attribute in port_def.attributes.values():
                if is_control_attribute(attribute.name):
                    continue
                connector_name = _connector_name(
                    port_usage, attribute.name, flat, index
                )
                element.add_connector(
                    name=connector_name,
                    kind=to_fmi_direction_definition(port_usage.direction),
                    type_name=attribute.effective_type_name,
                )

    has_interface = parameter_interface(architecture, part_def) is not None
    if parameter_model and has_interface:
        for attribute in parameter_declarations(architecture, part_def):
            for item in parameter_items(attribute, base_index=base_index):
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
        src_port_def, src_port_usage = _endpoint_port_def(
            part_def, architecture, conn.source_part, conn.source_port
        )
        dst_port_def, dst_port_usage = _endpoint_port_def(
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

        src_flat = flat_connector(src_port_def)
        dst_flat = flat_connector(dst_port_def)
        src_indices = _port_indices(src_port_usage)
        dst_indices = _port_indices(dst_port_usage)
        if src_indices != dst_indices:
            raise ValueError(
                f"Connection '{conn.key}' joins ports with different "
                f"multiplicity: {src_port_usage.name}"
                f"{_multiplicity_text(src_port_usage)} and "
                f"{dst_port_usage.name}{_multiplicity_text(dst_port_usage)}"
            )
        for index in src_indices:
            for attribute_name in src_port_def.attributes.keys():
                if is_control_attribute(attribute_name):
                    continue
                target_system.add_connection(
                    start_element=conn.source_part,
                    start_connector=_connector_name(
                        src_port_usage, attribute_name, src_flat, index
                    ),
                    end_element=conn.destination_part,
                    end_connector=_connector_name(
                        dst_port_usage, attribute_name, dst_flat, index
                    ),
                )


def _write_elements(
    parent: System,
    part_def: PartDefinition,
    architecture: Architecture,
    *,
    parameter_model: bool,
    type_check: bool,
    base_index: int = 0,
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
            _add_part_connectors(nested, child, architecture, parameter_model, base_index=base_index)
            _write_elements(
                nested,
                child,
                architecture,
                parameter_model=parameter_model,
                type_check=type_check,
                base_index=base_index,
            )
            continue

        component = parent.add_component(
            part_name,
            source=component_source(child, metadata),
            component_type="application/x-fmu-sharedlibrary",
            implementation=component_implementation(metadata),
        )
        _add_part_connectors(component, child, architecture, parameter_model, base_index=base_index)

    _add_connections(parent, part_def, architecture, type_check)


def build_ssd(
    ssd: SSD,
    system: PartDefinition,
    architecture: Architecture,
    type_check=True,
    parameter_set_prefix: str = "parameter_sets",
    *,
    base_index: int = 0,
) -> None:
    validate_role_markers(architecture)
    if is_analysis(architecture, system):
        raise ValueError(
            f"Composition '{system.name}' is an Analysis; analyses generate scenario "
            "data and are never exported as an SSD or SSP"
        )
    if ssp_metadata(architecture, system) is not None:
        raise ValueError(
            f"Composition '{system.name}' selects an external SSP source via "
            "'ssp_meta'; it is an analysis-only boundary and cannot be exported"
        )
    top = ssd.new_system(system.name)
    ssd.rename(system.name)

    if parameter_interface(architecture, system) is not None:
        raise ValueError(
            "Top-level composition parameter interfaces are not supported; "
            "attach parameter interfaces to component usages"
        )

    validate_parameter_dialect(architecture, system, policy=SSP_POLICY)
    parameter_model = has_parameter_dialect(architecture, system, policy=SSP_POLICY)
    specs = mapping_specs(architecture, system, policy=SSP_POLICY, base_index=base_index) if parameter_model else []

    _add_part_connectors(top, system, architecture, parameter_model, base_index=base_index)
    _write_elements(
        top,
        system,
        architecture,
        parameter_model=parameter_model,
        type_check=type_check,
        base_index=base_index,
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
    *,
    includes: Sequence[Path | str] = (),
    base_index: int = 0,
) -> Path:
    """Write an SSD for one composition.

    ``base_index`` is the first array index emitted in parameter connector
    names, e.g. 0 -> ``waypointX_km[0]`` and 1 -> ``waypointX_km[1]``. Data
    ports keep their FMI-style 1-based indices regardless.

    ``includes`` names additional definition roots (files or directories)
    merged into the loaded architecture; pass
    :func:`pycps_sysml2.core_definitions` to supply the dialect core. Empty
    (the default) loads only the model's own declarations.
    """
    architecture = load(architecture_path, *includes)
    system = architecture.get_part_def(composition)
    canonical = None
    if selections:
        architecture, canonical = resolve_selected(
            architecture, system, selections, roles=SSP_ROLES
        )
        system = architecture.get_part_def(composition)
    enforce_constraints(architecture, composition, canonical)
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
            base_index=base_index,
        )
    return output_path
