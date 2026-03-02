"""Main CLI entrypoint for pyssp_sysml2."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from pyssp_sysml2.fmi import generate_model_descriptions
from pyssp_sysml2.paths import TEST_ARCHITECTURE_DIR, TEST_COMPOSITION_NAME, GENERATED_DIR
from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.ssv import generate_parameter_set
from pyssp_sysml2.sync import sync_sysml_from_ssd


def _add_common_architecture_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--architecture",
        type=Path,
        default=TEST_ARCHITECTURE_DIR,
        help="Path to SysML architecture directory or a file inside it.",
    )
    parser.add_argument(
        "--composition",
        default=TEST_COMPOSITION_NAME,
        help="Top-level composition part definition name.",
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="pyssp", description=__doc__)
    root_subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = root_subparsers.add_parser("generate", help="Generate SSP/FMI artifacts")
    generate_subparsers = generate_parser.add_subparsers(dest="artifact", required=True)
    sync_parser = root_subparsers.add_parser(
        "sync", help="Sync external artifacts back into SysML"
    )
    sync_subparsers = sync_parser.add_subparsers(dest="artifact", required=True)

    ssd_parser = generate_subparsers.add_parser("ssd", help="Generate SystemStructure.ssd")
    _add_common_architecture_args(ssd_parser)
    ssd_parser.add_argument(
        "--output",
        type=Path,
        default=GENERATED_DIR / "SystemStructure.ssd",
        help="Output SSD file path.",
    )

    ssv_parser = generate_subparsers.add_parser("ssv", help="Generate parameter .ssv")
    _add_common_architecture_args(ssv_parser)
    ssv_parser.add_argument(
        "--output",
        type=Path,
        default=GENERATED_DIR / "parameters.ssv",
        help="Output SSV file path.",
    )

    fmi_parser = generate_subparsers.add_parser("fmi", help="Generate FMI model descriptions")
    _add_common_architecture_args(fmi_parser)
    fmi_parser.add_argument(
        "--output-dir",
        type=Path,
        default=GENERATED_DIR / "model_descriptions",
        help="Output directory for modelDescription.xml files.",
    )

    sync_ssd_parser = sync_subparsers.add_parser(
        "ssd", help="Sync SysML composition connections from an external SSD"
    )
    _add_common_architecture_args(sync_ssd_parser)
    sync_ssd_parser.add_argument(
        "--ssd",
        type=Path,
        required=True,
        help="Path to external SystemStructure.ssd used as sync source.",
    )
    sync_ssd_parser.add_argument(
        "--output-architecture-dir",
        type=Path,
        default=None,
        help="Optional output directory for updated .sysml files (defaults to architecture source).",
    )

    args = parser.parse_args(argv)

    try:
        if args.command == "generate" and args.artifact == "ssd":
            output = generate_ssd(args.architecture, args.output, args.composition)
            print(f"SSD written to {output}")
            return 0

        if args.command == "generate" and args.artifact == "ssv":
            output = generate_parameter_set(args.architecture, args.output, args.composition)
            print(f"Wrote {output}")
            return 0

        if args.command == "generate" and args.artifact == "fmi":
            written = generate_model_descriptions(
                args.architecture, args.output_dir, args.composition
            )
            if not written:
                print("No components matched the provided criteria.")
                return 1
            for path in written:
                print(f"Wrote {path}")
            return 0

        if args.command == "sync" and args.artifact == "ssd":
            written = sync_sysml_from_ssd(
                architecture_path=args.architecture,
                ssd_path=args.ssd,
                composition=args.composition,
                output_architecture_dir=args.output_architecture_dir,
            )
            for path in written:
                print(f"Wrote {path}")
            return 0

    except Exception as exc:  # noqa: BLE001
        print(f"[error] {exc}")
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
