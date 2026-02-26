#!/usr/bin/env python3
"""Generate an SSP parameter set (SSV) from architecture attributes."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Optional

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyssp_standard.ssv import SSV

from pycps_sysmlv2 import SysMLAttribute, load_system
from pyssp_sysml2.paths import (
    ARCHITECTURE_DIR,
    GENERATED_DIR,
    COMPOSITION_NAME,
    ensure_parent_dir,
)
from pyssp_sysml2.fmi_helpers import format_value

DEFAULT_ARCH_PATH = ARCHITECTURE_DIR
DEFAULT_OUTPUT = GENERATED_DIR / "parameters.ssv"


def populate_parameter_set(ssv: SSV, parameter_pairs: Iterable[tuple[str, SysMLAttribute]]) -> None:
    # print("Populate parameter set")
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
    # print("Populate parameter set -- DONE")


#  Evaluate why this is needed...
def _strip_none_parameter_attrs(ssv: SSV) -> None:
    for parameter in ssv.parameters:
        type_value = parameter["type_value"]
        type_value.parameter = {
            key: value
            for key, value in type_value.parameter.items()
            if value is not None
        }

def generate_parameter_set(
    architecture_path: Path,
    output_path: Path,
    composition: str = None,
) -> Path:
    
    system = load_system(architecture_path, composition)

    attributes = []

    for part_name, part in system.parts.items():
        for attr_name, attr in part.part_def.attributes.items():
            attributes.append((part_name, attr_name, attr))

    pairs = [(f"{p}.{a}", attr) for p, a, attr in attributes]

    ensure_parent_dir(output_path)
    with SSV(output_path, mode="w", name="ArchitecturalDefaults") as ssv:
        populate_parameter_set(ssv, pairs)
        _strip_none_parameter_attrs(ssv)
    return output_path


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--architecture",
        type=Path,
        default=DEFAULT_ARCH_PATH,
        help="Path to the SysML architecture directory or a file inside it.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Destination for the generated .ssv file.",
    )
    parser.add_argument(
        "--composition",
        default=COMPOSITION_NAME,
        help="Optional subset of component names to include.",
    )
    args = parser.parse_args(argv)

    try:
        output_path = generate_parameter_set(args.architecture, args.output, args.composition)
    except Exception as exc:  # noqa: BLE001
        print(f"[error] {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
