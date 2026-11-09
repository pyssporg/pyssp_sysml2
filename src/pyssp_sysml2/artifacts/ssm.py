"""SSP parameter-mapping (SSM) generation from SysML ``bind`` statements."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pyssp_standard import SSM

from pycps_sysml2.model import load
from pycps_sysml2.parameters.dialect.mapping import mapping_specs
from pycps_sysml2.parameters.policy import SSP_POLICY

from pyssp_sysml2.core.paths import ensure_directory


def generate_parameter_mappings(
    architecture_path: Path,
    output_dir: Path,
    composition: str,
    *,
    includes: Sequence[Path | str] = (),
    base_index: int = 0,
) -> list[Path]:
    """Write one SSM file per (set, component usage) explicit mapping.

    Whole-object identity bindings need no SSM; they map to an SSP
    ``ParameterBinding`` with ``prefix="<component>."`` instead.

    ``base_index`` is the first array index emitted in mapping source and
    target names, e.g. 0 -> ``waypoints_x_km[0]`` and 1 -> ``waypoints_x_km[1]``.

    ``includes`` names additional definition roots (files or directories)
    merged into the loaded architecture; pass
    :func:`pycps_sysml2.core_definitions` to supply the dialect core. Empty
    (the default) loads only the model's own declarations.
    """
    architecture = load(architecture_path, *includes)
    system = architecture.get_part_def(composition)

    written: list[Path] = []
    for spec in mapping_specs(
        architecture, system, policy=SSP_POLICY, base_index=base_index
    ):
        if spec.identity:
            continue
        component_name = spec.component_name.replace(".", "_")
        output_path = output_dir / f"{spec.set_name}_{component_name}.ssm"
        ensure_directory(output_dir)
        with SSM(output_path, mode="w") as ssm:
            for source, target in spec.entries:
                ssm.add_mapping(source, target)
        written.append(output_path)
    return sorted(written)
