"""Generic SSV generation helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pyssp_standard.ssv import SSV

from pyssp_sysml2.fmi_helpers import format_value
from pyssp_sysml2.paths import ensure_parent_dir
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
                ssv.add_parameter(indexed_name, ptype=data_type, value=formatted)
            continue

        formatted = format_value(data_type, attr.value)
        ssv.add_parameter(name, ptype=data_type, value=formatted)


def _strip_none_parameter_attrs(ssv: SSV) -> None:
    for parameter in ssv.parameters:
        type_value = parameter["type_value"]
        type_value.parameter = {
            key: value
            for key, value in type_value.parameter.items()
            if value is not None
        }


def generate_parameter_set(architecture_path: Path, output_path: Path, composition: str) -> Path:
    architecture = load(architecture_path)
    system = architecture.get_part_def(composition)

    pairs = []
    for part_name, part_usage in system.parts.items():
        part_def = architecture.resolve_part(part_usage)
        if part_def is None:
            raise ValueError(f"Unresolved part definition for {part_usage.name}")
        for attr_name, attr in part_def.attributes.items():
            pairs.append((f"{part_name}.{attr_name}", attr))

    ensure_parent_dir(output_path)
    with SSV(output_path, mode="w", name="ArchitecturalDefaults") as ssv:
        populate_parameter_set(ssv, pairs)
        _strip_none_parameter_attrs(ssv)
    return output_path
