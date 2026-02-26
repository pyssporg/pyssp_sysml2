"""Generic SSV generation helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pycps_sysmlv2 import SysMLAttribute, load_system
from pyssp_standard.ssv import SSV

from pyssp_sysml2.fmi_helpers import format_value
from pyssp_sysml2.paths import ensure_parent_dir


def populate_parameter_set(ssv: SSV, parameter_pairs: Iterable[tuple[str, SysMLAttribute]]) -> None:
    for name, attr in parameter_pairs:
        data_type = attr.type.primitive_type_str()
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
    system = load_system(architecture_path, composition)

    pairs = []
    for part_name, part in system.parts.items():
        for attr_name, attr in part.part_def.attributes.items():
            pairs.append((f"{part_name}.{attr_name}", attr))

    ensure_parent_dir(output_path)
    with SSV(output_path, mode="w", name="ArchitecturalDefaults") as ssv:
        populate_parameter_set(ssv, pairs)
        _strip_none_parameter_attrs(ssv)
    return output_path
