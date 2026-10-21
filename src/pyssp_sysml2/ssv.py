"""Generic SSV generation helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pyssp_standard.ssv import SSV

from pyssp_sysml2.fmi_helpers import format_value
from pyssp_sysml2.paths import ensure_parent_dir
from pyssp_sysml2.sysml import is_control_attribute
from pyssp_sysml2.sysml_model import Attribute, load


def populate_parameter_set(ssv: SSV, parameter_pairs: Iterable[tuple[str, Attribute]]) -> None:
    for name, attr in parameter_pairs:
        data_type = attr.primitive_type_str()
        if attr.value is None:
            continue

        if isinstance(attr.value, (list, tuple)):
            for idx, item in enumerate(attr.value, start=0):
                indexed_name = f"{name}[{idx}]"
                formatted = format_value(data_type, item)
                ssv.xml.add_parameter(indexed_name, ptype=data_type, value=formatted)
            continue

        formatted = format_value(data_type, attr.value)
        ssv.xml.add_parameter(name, ptype=data_type, value=formatted)


def generate_parameter_set(architecture_path: Path, output_path: Path, composition: str) -> Path:
    architecture = load(architecture_path)
    system = architecture.get_part_def(composition)

    pairs = []
    for part_name, part_usage in system.parts.items():
        part_def = architecture.resolve_part(part_usage)
        if part_def is None:
            raise ValueError(f"Unresolved part definition for {part_usage.name}")
        for attr_name, attr in part_def.attributes.items():
            if is_control_attribute(attr_name):
                continue
            pairs.append((f"{part_name}.{attr_name}", attr))

    ensure_parent_dir(output_path)
    with SSV(output_path, mode="w") as ssv:
        ssv.xml.name = "ArchitecturalDefaults"
        populate_parameter_set(ssv, pairs)
    return output_path
