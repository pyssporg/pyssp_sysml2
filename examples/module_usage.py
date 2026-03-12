"""Example Python API usage for pyssp_sysml2.

Run from repository root:

    PYTHONPATH=src python3 examples/module_usage.py

Optional arguments:

    PYTHONPATH=src python3 examples/module_usage.py \
      --architecture examples/aircraft_subset \
      --composition AircraftComposition \
      --output-root build/generated

    PYTHONPATH=src python3 examples/module_usage.py \
      --architecture examples/aircraft_subset \
      --composition AircraftComposition \
      --output-root build/generated \
      --bootstrap-architecture-dir build/new_architecture
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pyssp_sysml2.fmi import generate_model_descriptions
from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.ssv import generate_parameter_set
from pyssp_sysml2.sysml import generate_sysml_from_ssd
from pyssp_sysml2.sync import sync_sysml_from_ssd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--architecture",
        type=Path,
        default=Path("examples/aircraft_subset"),
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
    parser.add_argument(
        "--bootstrap-architecture-dir",
        type=Path,
        default=None,
        help="Optional output directory for a minimal SysML architecture generated from SSD.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    ssd_path = args.output_root / "SystemStructure.ssd"
    ssv_path = args.output_root / "parameters.ssv"
    fmi_dir = args.output_root / "model_descriptions"
    sync_dir = args.output_root / "synced_sysml"

    generate_ssd(args.architecture, ssd_path, args.composition)
    generate_parameter_set(args.architecture, ssv_path, args.composition)
    written = generate_model_descriptions(args.architecture, fmi_dir, args.composition)
    bootstrapped = []
    if args.bootstrap_architecture_dir is not None:
        bootstrapped = [
            generate_sysml_from_ssd(
                ssd_path,
                args.bootstrap_architecture_dir / "architecture.sysml",
                args.composition,
            )
        ]
    synced = sync_sysml_from_ssd(
        args.architecture,
        ssd_path,
        args.composition,
        output_architecture_dir=sync_dir,
    )

    print(f"SSD: {ssd_path}")
    print(f"SSV: {ssv_path}")
    print("FMI model descriptions:")
    for path in written:
        print(f"  - {path}")
    print("Synced SysML files:")
    for path in synced:
        print(f"  - {path}")
    if bootstrapped:
        print("Bootstrapped SysML files:")
        for path in bootstrapped:
            print(f"  - {path}")


if __name__ == "__main__":
    main()
