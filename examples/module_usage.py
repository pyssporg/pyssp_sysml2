"""Example Python API usage for pyssp_sysml2.

Run from repository root:

    PYTHONPATH=src python examples/module_usage.py

Optional arguments:

    PYTHONPATH=src python examples/module_usage.py \
      --architecture tests/fixtures/aircraft_subset \
      --composition AircraftComposition \
      --output-root build/generated
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pyssp_sysml2.fmi import generate_model_descriptions
from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.ssv import generate_parameter_set


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--architecture",
        type=Path,
        default=Path("tests/fixtures/aircraft_subset"),
        help="Path to SysML architecture directory or a file inside it.",
    )
    parser.add_argument(
        "--composition",
        default="AircraftComposition",
        help="Top-level composition part definition name.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("build/generated"),
        help="Output root directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    ssd_path = args.output_root / "SystemStructure.ssd"
    ssv_path = args.output_root / "parameters.ssv"
    fmi_dir = args.output_root / "model_descriptions"

    generate_ssd(args.architecture, ssd_path, args.composition)
    generate_parameter_set(args.architecture, ssv_path, args.composition)
    written = generate_model_descriptions(args.architecture, fmi_dir, args.composition)

    print(f"SSD: {ssd_path}")
    print(f"SSV: {ssv_path}")
    print("FMI model descriptions:")
    for path in written:
        print(f"  - {path}")


if __name__ == "__main__":
    main()
