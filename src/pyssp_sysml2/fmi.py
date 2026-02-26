"""Generic FMI modelDescription generation helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import NAMESPACE_URL, uuid5
import xml.etree.ElementTree as ET

from pycps_sysmlv2 import SysMLPartDefinition, load_system

from pyssp_sysml2.fmi_helpers import format_value, map_fmi_type
from pyssp_sysml2.paths import BUILD_DIR, ensure_directory

CO_SIMULATION_ATTRS = {
    "modelIdentifier": "",
}


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
    part: SysMLPartDefinition, starting_ref: int, starting_index: int
) -> tuple[list[VariableSpec], int, int]:
    variables: list[VariableSpec] = []
    value_ref = starting_ref
    value_index = starting_index

    for port, port_def, attr in part.get_port_attributes():
        spec = VariableSpec(
            name=f"{port.name}.{attr.name}",
            causality="input" if port.direction == "in" else "output",
            value_reference=value_ref,
            fmi_type=map_fmi_type(attr.type.as_string()),
            description=attr.doc or port.doc or (port_def.doc if port_def else None),
            index=value_index,
        )
        variables.append(spec)
        value_ref += 1
        value_index += 1

    return variables, value_ref, value_index


def _parameter_variables(
    part: SysMLPartDefinition, starting_ref: int, starting_index: int
) -> tuple[list[VariableSpec], int, int]:
    variables: list[VariableSpec] = []
    value_ref = starting_ref
    value_index = starting_index

    for _attr_name, attr in part.attributes.items():
        if attr.is_list():
            for idx, item in enumerate(attr.value, start=0):
                variables.append(
                    VariableSpec(
                        name=f"{attr.name}[{idx}]",
                        causality="parameter",
                        value_reference=value_ref,
                        fmi_type="Real",
                        variability="fixed",
                        description=attr.doc,
                        start_value=format_value("Real", item),
                        index=value_index,
                    )
                )
                value_ref += 1
                value_index += 1
            continue

        fmi_type = map_fmi_type(attr.type.as_string())
        variables.append(
            VariableSpec(
                name=attr.name,
                causality="parameter",
                value_reference=value_ref,
                fmi_type=fmi_type,
                variability="fixed",
                description=attr.doc,
                start_value=format_value(fmi_type, attr.value),
                index=value_index,
            )
        )
        value_ref += 1
        value_index += 1

    return variables, value_ref, value_index


def _get_variables(part: SysMLPartDefinition) -> list[VariableSpec]:
    value_ref = 0
    index = 1

    parameter_vars, value_ref, index = _parameter_variables(part, value_ref, index)
    port_vars, value_ref, index = _port_attribute_variables(part, value_ref, index)

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
    part: SysMLPartDefinition, package_name: str
) -> ET.ElementTree:
    timestamp = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    guid = str(uuid5(NAMESPACE_URL, f"pyssp_sysml2/{package_name}/{part.name}"))

    root = ET.Element(
        "fmiModelDescription",
        attrib={
            "fmiVersion": "2.0",
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
    variables = _get_variables(part)
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
) -> list[Path]:
    ensure_directory(output_dir)
    ensure_directory(BUILD_DIR / "fmu_pre")

    system = load_system(architecture_path, composition)

    written: list[Path] = []
    for _part_inst_name, part_ref in system.parts.items():
        component_dir = output_dir / part_ref.part_name
        output_path = component_dir / "modelDescription.xml"
        ensure_directory(component_dir)

        tree = _build_model_description_tree(part_ref.part_def, system.name)
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        written.append(output_path)

    return written
