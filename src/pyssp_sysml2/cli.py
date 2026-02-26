"""Main CLI entrypoint for pyssp_sysml2."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from pyssp_sysml2.fmi import generate_model_descriptions
from pyssp_sysml2.paths import TEST_ARCHITECTURE_DIR, TEST_COMPOSITION_NAME, GENERATED_DIR
from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.ssv import generate_parameter_set


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

    except Exception as exc:  # noqa: BLE001
        print(f"[error] {exc}")
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
