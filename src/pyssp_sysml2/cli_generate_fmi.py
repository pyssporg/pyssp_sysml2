"""CLI for FMI modelDescription generation."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from pyssp_sysml2.fmi import generate_model_descriptions
from pyssp_sysml2.paths import TEST_ARCHITECTURE_DIR, TEST_COMPOSITION_NAME, GENERATED_DIR

DEFAULT_ARCH_PATH = TEST_ARCHITECTURE_DIR
DEFAULT_OUTPUT_DIR = GENERATED_DIR / "model_descriptions"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--architecture",
        type=Path,
        default=DEFAULT_ARCH_PATH,
        help="Path to the SysML architecture directory or a file within it.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory that will contain one sub-folder per component, each with a modelDescription.xml.",
    )
    parser.add_argument(
        "--composition",
        default=TEST_COMPOSITION_NAME,
        help="Optional subset of component instance/definition names to generate.",
    )
    args = parser.parse_args(argv)

    try:
        written = generate_model_descriptions(
            args.architecture, args.output_dir, args.composition
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[error] {exc}", file=sys.stderr)
        return 1

    if not written:
        print("No components matched the provided criteria.")
        return 1

    for path in written:
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
