"""Generic SSV generation helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pyssp_standard.ssv import SSV

from pyssp_sysml2.control import is_control_attribute
from pyssp_sysml2.fmi_helpers import format_value
from pyssp_sysml2.parameters import (
    fixed_count,
    parameter_sets_for_generation,
    validate_applied_sets,
    validate_marker_definitions,
    validate_parameter_dialect,
)
from pyssp_sysml2.paths import ensure_directory, ensure_parent_dir
from pyssp_sysml2.sysml_model import Attribute, AttributeDefinition, load


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


def write_parameter_set(
    definition: AttributeDefinition, output_path: Path
) -> Path:
    """Write one parameter-set definition as an SSV file."""
    pairs = [
        (name, attribute)
        for name, attribute in definition.attributes.items()
        if not is_control_attribute(name) and attribute.value is not None
    ]
    if not pairs:
        raise ValueError(f"Parameter set '{definition.name}' has no values")
    for name, attribute in pairs:
        if not attribute.multiplicity:
            continue
        count = fixed_count(attribute.multiplicity, name)
        if not isinstance(attribute.value, tuple) or len(attribute.value) != count:
            raise ValueError(
                f"Parameter set member '{name}' must provide {count} values "
                f"for [{attribute.multiplicity}]"
            )

    ensure_parent_dir(output_path)
    with SSV(output_path, mode="w") as ssv:
        ssv.xml.name = definition.name
        populate_parameter_set(ssv, pairs)
    return output_path


def generate_parameter_sets(
    architecture_path: Path,
    output_dir: Path,
    composition: str,
    *,
    set_names: Iterable[str] | None = None,
    all_sets: bool = False,
    output_path: Path | None = None,
) -> list[Path]:
    """Generate one SSV per parameter-set definition.

    With ``output_path`` exactly one set may be selected. Otherwise files are
    written as ``<output_dir>/<SetName>.ssv``.
    """
    architecture = load(architecture_path)
    system = architecture.get_part_def(composition)
    validate_marker_definitions(architecture)
    validate_parameter_dialect(architecture, system)
    validate_applied_sets(architecture, system)
    definitions = parameter_sets_for_generation(
        architecture, system, set_names=list(set_names) if set_names else None,
        all_sets=all_sets,
    )
    if not definitions:
        return []

    if output_path is not None:
        if len(definitions) != 1:
            raise ValueError(
                "A single --output file requires exactly one parameter set; "
                f"selected {len(definitions)}"
            )
        return [write_parameter_set(definitions[0], output_path)]

    ensure_directory(output_dir)
    return [
        write_parameter_set(definition, output_dir / f"{definition.name}.ssv")
        for definition in definitions
    ]
