"""Generic FMI modelDescription generation helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import NAMESPACE_URL, uuid5
import xml.etree.ElementTree as ET

from pyssp_sysml2.core.control import is_control_attribute
from pyssp_sysml2.core.fmi_helpers import format_value, map_fmi_type
from pyssp_sysml2.parameters.dialect.composition import (
    component_definitions,
    validate_parameter_dialect,
)
from pyssp_sysml2.parameters.dialect.declarations import (
    parameter_declarations,
    parameter_items,
)
from pyssp_sysml2.parameters.dialect.markers import is_parameter_interface
from pyssp_sysml2.core.paths import ensure_directory
from pyssp_sysml2.model import Architecture, PartDefinition, load

CO_SIMULATION_ATTRS = {
    "modelIdentifier": "",
}

#: FMI version emitted for every generated model description.
FMI_VERSION = "2.0"

#: Namespace the FMI ``guid`` is derived from; changing it changes every guid.
GUID_NAMESPACE = NAMESPACE_URL


def utc_now() -> datetime:
    """Current time in UTC; the clock hook for ``generationDateAndTime``.

    The default source of generation time. Tests replace it (or pass
    ``generation_time``) to make generation reproducible.
    """
    return datetime.now(timezone.utc)


def format_generation_timestamp(moment: datetime) -> str:
    """Render a timezone-aware time as an FMI ``dateTime`` with second precision."""
    if moment.tzinfo is None:
        raise ValueError("generation time must be timezone-aware, e.g. from utc_now()")
    return (
        moment.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


@dataclass
class VariableSpec:
    name: str
    causality: str
    value_reference: int
    index: int
    fmi_type: str
    variability: Optional[str] = None
    description: Optional[str] = None
    start_value: Optional[str] = None


def _port_attribute_variables(
    part: PartDefinition,
    architecture: Architecture,
    starting_ref: int,
    starting_index: int,
) -> tuple[list[VariableSpec], int, int]:
    variables: list[VariableSpec] = []
    value_ref = starting_ref
    value_index = starting_index

    for port_usage in part.ports.values():
        port_def = architecture.resolve_port(port_usage)
        if port_def is None:
            raise ValueError(f"Unresolved port definition for {part.name}.{port_usage.name}")
        if is_parameter_interface(port_def):
            # Emitted as parameter variables, not as input/output ports.
            continue
        for attr in port_def.attributes.values():
            if is_control_attribute(attr.name):
                continue
            spec = VariableSpec(
                name=f"{port_usage.name}.{attr.name}",
                causality="input" if port_usage.direction == "in" else "output",
                value_reference=value_ref,
                fmi_type=map_fmi_type(attr.effective_type_name),
                description=attr.doc or port_usage.doc or port_def.doc,
                index=value_index,
            )
            variables.append(spec)
            value_ref += 1
            value_index += 1

    return variables, value_ref, value_index


def _parameter_variables(
    part: PartDefinition,
    architecture: Architecture,
    starting_ref: int,
    starting_index: int,
) -> tuple[list[VariableSpec], int, int]:
    variables: list[VariableSpec] = []
    value_ref = starting_ref
    value_index = starting_index

    for attribute in parameter_declarations(architecture, part):
        fmi_type = map_fmi_type(attribute.primitive_type_str())
        for item in parameter_items(attribute):
            variables.append(
                VariableSpec(
                    name=item.name,
                    causality="parameter",
                    value_reference=value_ref,
                    fmi_type=fmi_type,
                    variability="fixed",
                    description=attribute.doc,
                    start_value=(
                        format_value(fmi_type, item.value)
                        if item.value is not None
                        else None
                    ),
                    index=value_index,
                )
            )
            value_ref += 1
            value_index += 1

    return variables, value_ref, value_index


def _get_variables(
    part: PartDefinition, architecture: Architecture
) -> list[VariableSpec]:
    value_ref = 0
    index = 1

    parameter_vars, value_ref, index = _parameter_variables(
        part, architecture, value_ref, index
    )
    port_vars, value_ref, index = _port_attribute_variables(
        part, architecture, value_ref, index
    )

    return parameter_vars + port_vars


def _write_scalar_variable(parent: ET.Element, spec: VariableSpec) -> None:
    attrib = {
        "name": spec.name,
        "valueReference": str(spec.value_reference),
    }
    if spec.causality:
        attrib["causality"] = spec.causality
    if spec.variability:
        attrib["variability"] = spec.variability
    if spec.description:
        attrib["description"] = spec.description

    scalar = ET.SubElement(parent, "ScalarVariable", attrib=attrib)
    data_type = ET.SubElement(scalar, spec.fmi_type)
    if spec.start_value is not None:
        data_type.set("start", spec.start_value)


def _build_model_description_tree(
    part: PartDefinition,
    package_name: str,
    architecture: Architecture,
    *,
    generation_time: Optional[datetime] = None,
) -> ET.ElementTree:
    timestamp = format_generation_timestamp(
        generation_time if generation_time is not None else utc_now()
    )
    guid = str(
        uuid5(GUID_NAMESPACE, f"pyssp_sysml2/{package_name}/{part.name}")
    )

    root = ET.Element(
        "fmiModelDescription",
        attrib={
            "fmiVersion": FMI_VERSION,
            "modelName": f"{package_name}.{part.name}",
            "guid": f"{{{guid}}}",
            "description": part.doc or "",
            "version": "1.0",
            "generationTool": "pyssp_sysml2 tooling",
            "generationDateAndTime": timestamp,
            "variableNamingConvention": "structured",
            "numberOfEventIndicators": "0",
        },
    )

    co_sim_attrs = dict(CO_SIMULATION_ATTRS)
    co_sim_attrs["modelIdentifier"] = part.name
    ET.SubElement(root, "CoSimulation", attrib=co_sim_attrs)

    model_vars = ET.SubElement(root, "ModelVariables")
    variables = _get_variables(part, architecture)
    for spec in variables:
        _write_scalar_variable(model_vars, spec)

    model_structure = ET.SubElement(root, "ModelStructure")
    outputs_elem = ET.SubElement(model_structure, "Outputs")
    initial_elem = ET.SubElement(model_structure, "InitialUnknowns")

    for var in [x for x in variables if x.causality == "output"]:
        ET.SubElement(outputs_elem, "Unknown", attrib={"index": str(var.index)})
        ET.SubElement(initial_elem, "Unknown", attrib={"index": str(var.index)})

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    return tree


def generate_model_descriptions(
    architecture_path: Path,
    output_dir: Path,
    composition: str,
    *,
    generation_time: Optional[datetime] = None,
) -> list[Path]:
    """Write one ``modelDescription.xml`` per leaf component under ``output_dir``.

    Generated files go only below ``output_dir``. ``generation_time`` fixes the
    FMI ``generationDateAndTime``; when omitted, :func:`utc_now` supplies the
    current UTC time.
    """
    ensure_directory(output_dir)

    architecture = load(architecture_path)
    system = architecture.get_part_def(composition)
    validate_parameter_dialect(architecture, system)

    written: list[Path] = []
    for part_def in sorted(
        component_definitions(architecture, system),
        key=lambda definition: definition.name,
    ):
        if part_def.parts:
            continue
        component_dir = output_dir / part_def.name
        output_path = component_dir / "modelDescription.xml"
        ensure_directory(component_dir)

        tree = _build_model_description_tree(
            part_def,
            system.name,
            architecture,
            generation_time=generation_time,
        )
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        written.append(output_path)

    return written
