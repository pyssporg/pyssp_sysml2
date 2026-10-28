"""Main CLI entrypoint for pyssp_sysml2."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from pyssp_sysml2.artifacts.fmi import generate_model_descriptions
from pyssp_sysml2.core.paths import (
    DEFAULT_ARCH_PATH,
    DEFAULT_COMPOSITION_NAME,
    GENERATED_DIR,
)
from pyssp_sysml2.artifacts.ssd import generate_ssd
from pyssp_sysml2.artifacts.ssm import generate_parameter_mappings
from pyssp_sysml2.artifacts.ssp import DEFAULT_PARAMETER_SET_PREFIX, generate_ssp
from pyssp_sysml2.artifacts.ssv import generate_parameter_sets
from pyssp_sysml2.artifacts.study import generate_study
from pyssp_sysml2.sysml.generate import generate_sysml_from_ssd
from pyssp_sysml2.sysml.sync import sync_sysml_from_ssd


def _add_common_architecture_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--architecture",
        type=Path,
        default=DEFAULT_ARCH_PATH,
        help="Path to SysML architecture directory or a file inside it.",
    )
    parser.add_argument(
        "--composition",
        default=DEFAULT_COMPOSITION_NAME,
        help="Top-level composition part definition name.",
    )
    parser.add_argument(
        "--select",
        action="append",
        default=None,
        metavar="KEY=VARIANT",
        help=(
            "Select one variant for a variation point, keyed by part-usage path "
            "(repeatable), e.g. source=stepImplementation."
        ),
    )


def _parse_selections(values: list[str] | None) -> dict[str, str] | None:
    """Parse repeatable ``--select KEY=VARIANT`` values into a mapping."""
    if not values:
        return None
    selections: dict[str, str] = {}
    for value in values:
        key, separator, variant = value.partition("=")
        key = key.strip()
        variant = variant.strip()
        if not separator or not key or not variant:
            raise ValueError(
                f"Invalid --select value '{value}'; expected KEY=VARIANT, for "
                "example source=stepImplementation."
            )
        if key in selections:
            raise ValueError(
                f"Duplicate selection for '{key}'; pass each variation point once."
            )
        selections[key] = variant
    return selections


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="pyssp", description=__doc__)
    root_subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = root_subparsers.add_parser(
        "generate", help="Generate SSP/FMI/SysML artifacts"
    )
    generate_subparsers = generate_parser.add_subparsers(dest="artifact", required=True)
    sync_parser = root_subparsers.add_parser(
        "sync", help="Sync external artifacts back into SysML"
    )
    sync_subparsers = sync_parser.add_subparsers(dest="artifact", required=True)

    ssd_parser = generate_subparsers.add_parser(
        "ssd", help="Generate SystemStructure.ssd"
    )
    _add_common_architecture_args(ssd_parser)
    ssd_parser.add_argument(
        "--output",
        type=Path,
        default=GENERATED_DIR / "SystemStructure.ssd",
        help="Output SSD file path.",
    )
    ssd_parser.add_argument(
        "--skip_type_check",
        action="store_false",
        help="avoid typecheck during connection link",
    )
    ssd_parser.add_argument(
        "--parameter-set-prefix",
        default="parameter_sets",
        help=(
            "Relative directory used in SSD ParameterBinding sources, "
            "e.g. 'parameter_sets' -> 'parameter_sets/<Set>.ssv'."
        ),
    )

    ssp_parser = generate_subparsers.add_parser(
        "ssp", help="Package an SSP archive from SysML and built FMUs"
    )
    _add_common_architecture_args(ssp_parser)
    ssp_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Output .ssp archive path. Defaults to "
            "build/generated/<composition>.ssp."
        ),
    )
    ssp_parser.add_argument(
        "--parameter-set-prefix",
        default=DEFAULT_PARAMETER_SET_PREFIX,
        help=(
            "SSP-relative directory for packaged SSVs and SSD parameter "
            "bindings (default: resources/parameter_sets)."
        ),
    )
    ssp_parser.add_argument(
        "--fmu-root",
        type=Path,
        default=None,
        help=(
            "Base directory for relative fmu_meta.source paths "
            "(default: current working directory)."
        ),
    )
    ssp_parser.add_argument(
        "--skip-fmu-validation",
        action="store_false",
        dest="validate_fmus",
        help="Package FMUs without checking modelDescription names/implementation.",
    )
    ssp_parser.add_argument(
        "--allow-missing-fmus",
        action="store_true",
        dest="allow_missing_fmus",
        help=(
            "Export the SSP structure when a declared FMU source is not built "
            "yet. Populate the archive later with SSP.attach_fmu. A part "
            "without fmu_meta.source always exports with an empty source."
        ),
    )
    ssp_parser.add_argument(
        "--skip_type_check",
        action="store_false",
        help="Avoid type checking during connection linking.",
    )

    ssv_parser = generate_subparsers.add_parser("ssv", help="Generate parameter .ssv")
    _add_common_architecture_args(ssv_parser)
    ssv_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Output SSV file path for exactly one selected parameter set. "
            "Use --output-dir to write one file per set."
        ),
    )
    ssv_parser.add_argument(
        "--output-dir",
        type=Path,
        default=GENERATED_DIR / "parameter_sets",
        help="Output directory for parameter-set SSV files.",
    )
    ssv_parser.add_argument(
        "--set",
        action="append",
        default=None,
        help="Generate only this parameter set (repeatable).",
    )
    ssv_parser.add_argument(
        "--all-sets",
        action="store_true",
        help="Generate every parameter set in the architecture, applied or not.",
    )

    ssm_parser = generate_subparsers.add_parser(
        "ssm", help="Generate SSP parameter mappings"
    )
    _add_common_architecture_args(ssm_parser)
    ssm_parser.add_argument(
        "--output-dir",
        type=Path,
        default=GENERATED_DIR / "parameter_mappings",
        help="Output directory for .ssm parameter mapping files.",
    )

    study_parser = generate_subparsers.add_parser(
        "study", help="Generate study scenario SSV, SSM, and descriptor"
    )
    _add_common_architecture_args(study_parser)
    study_parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for study artifacts.",
    )
    study_parser.add_argument(
        "--model",
        required=True,
        help="Exported model name recorded in study.json.",
    )
    study_parser.add_argument(
        "--target-ssd",
        default="SystemStructure.ssd",
        help="SSD name the study targets inside the exported SSP.",
    )

    fmi_parser = generate_subparsers.add_parser(
        "fmi", help="Generate FMI model descriptions"
    )
    _add_common_architecture_args(fmi_parser)
    fmi_parser.add_argument(
        "--output-dir",
        type=Path,
        default=GENERATED_DIR / "model_descriptions",
        help="Output directory for modelDescription.xml files.",
    )

    sysml_parser = generate_subparsers.add_parser(
        "sysml", help="Generate a SysML file from an SSD"
    )
    sysml_parser.add_argument(
        "--ssd",
        type=Path,
        required=True,
        help="Path to source SystemStructure.ssd used to build the SysML model.",
    )
    sysml_parser.add_argument(
        "--composition",
        default=None,
        help="Optional top-level composition part definition name (defaults to the SSD system name).",
    )
    sysml_parser.add_argument(
        "--output",
        type=Path,
        default=GENERATED_DIR / "architecture.sysml",
        help="Output SysML file path.",
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
    sync_ssd_parser.add_argument(
        "--no-synthesize",
        action="store_false",
        dest="synthesize_external_parts",
        help="Disable synthesis of part definitions for SSD components that reference unknown FMU sources.",
    )

    args = parser.parse_args(argv)

    try:
        selections = _parse_selections(getattr(args, "select", None))
        if args.command == "generate" and args.artifact == "ssp":
            output = args.output or (GENERATED_DIR / f"{args.composition}.ssp")
            output = generate_ssp(
                args.architecture,
                output,
                args.composition,
                parameter_set_prefix=args.parameter_set_prefix,
                fmu_root=args.fmu_root,
                type_check=args.skip_type_check,
                validate_fmus=args.validate_fmus,
                allow_missing_fmus=args.allow_missing_fmus,
                selections=selections,
            )
            print(f"SSP written to {output}")
            return 0

        if args.command == "generate" and args.artifact == "ssd":
            output = generate_ssd(
                args.architecture,
                args.output,
                args.composition,
                args.skip_type_check,
                parameter_set_prefix=args.parameter_set_prefix,
                selections=selections,
            )
            print(f"SSD written to {output}")
            return 0

        if args.command == "generate" and args.artifact == "ssv":
            written = generate_parameter_sets(
                args.architecture,
                args.output_dir,
                args.composition,
                set_names=args.set,
                all_sets=args.all_sets,
                output_path=args.output,
            )
            if not written:
                print("No parameter sets matched.")
                return 1
            for path in written:
                print(f"Wrote {path}")
            return 0

        if args.command == "generate" and args.artifact == "ssm":
            written = generate_parameter_mappings(
                args.architecture, args.output_dir, args.composition
            )
            if not written:
                print(
                    "No parameter mappings (whole-object bindings use SSP prefixes)."
                )
                return 0
            for path in written:
                print(f"Wrote {path}")
            return 0

        if args.command == "generate" and args.artifact == "study":
            artifacts = generate_study(
                args.architecture,
                args.output_dir,
                args.composition,
                model_name=args.model,
                target_ssd=args.target_ssd,
                selections=selections,
            )
            if artifacts.ssv is not None:
                print(f"SSV written to {artifacts.ssv}")
            if artifacts.ssm is not None:
                print(f"SSM written to {artifacts.ssm}")
            print(f"Study descriptor written to {artifacts.descriptor}")
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

        if args.command == "generate" and args.artifact == "sysml":
            output = generate_sysml_from_ssd(args.ssd, args.output, args.composition)
            print(f"Wrote {output}")
            return 0

        if args.command == "sync" and args.artifact == "ssd":
            written = sync_sysml_from_ssd(
                architecture_path=args.architecture,
                ssd_path=args.ssd,
                composition=args.composition,
                output_architecture_dir=args.output_architecture_dir,
                synthesize_external_parts=args.synthesize_external_parts,
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
