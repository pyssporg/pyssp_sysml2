"""SSP parameter-mapping (SSM) generation from SysML ``bind`` statements."""

from __future__ import annotations

from pathlib import Path

from pyssp_standard.ssm import SSM

from pyssp_sysml2.parameters import mapping_specs
from pyssp_sysml2.paths import ensure_directory
from pyssp_sysml2.sysml_model import load


def generate_parameter_mappings(
    architecture_path: Path, output_dir: Path, composition: str
) -> list[Path]:
    """Write one SSM file per (set, component usage) explicit mapping.

    Whole-object identity bindings need no SSM; they map to an SSP
    ``ParameterBinding`` with ``prefix="<component>."`` instead.
    """
    architecture = load(architecture_path)
    system = architecture.get_part_def(composition)

    written: list[Path] = []
    for spec in mapping_specs(architecture, system):
        if spec.identity:
            continue
        output_path = output_dir / f"{spec.set_name}_{spec.part_name}.ssm"
        ensure_directory(output_dir)
        with SSM(output_path, mode="w") as ssm:
            for source, target in spec.entries:
                ssm.xml.add_mapping(source, target)
        written.append(output_path)
    return sorted(written)
