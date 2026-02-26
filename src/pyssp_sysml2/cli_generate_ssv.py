"""CLI for SSV generation."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from pyssp_sysml2.paths import TEST_ARCHITECTURE_DIR, TEST_COMPOSITION_NAME, GENERATED_DIR
from pyssp_sysml2.ssv import generate_parameter_set

DEFAULT_ARCH_PATH = TEST_ARCHITECTURE_DIR
DEFAULT_OUTPUT = GENERATED_DIR / "parameters.ssv"


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
        default=TEST_COMPOSITION_NAME,
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
