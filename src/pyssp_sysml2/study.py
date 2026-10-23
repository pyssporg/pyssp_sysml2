"""Generate study artifacts from a SysML ``Study`` composition.

A study composes one ``SspModel`` usage (conventionally ``sut``), applies zero
or one scenario parameter set, and declares one experiment. Generation writes a
``study.json`` descriptor and, when a set is applied, an SSV plus one SSM with
targets relative to the exported model root. A study without a set yields an
experiment-only descriptor for a model body that stays a checked-in SSP; that
body is named by the model's ``ssp_meta.source`` and recorded as
``model_source``. It never writes an SSD or an SSP.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pyssp_standard.ssm import SSM

from pyssp_sysml2.parameters import (
    applied_sets,
    mapping_specs,
    parameter_sets_for_generation,
    validate_marker_definitions,
    validate_parameter_dialect,
)
from pyssp_sysml2.paths import ensure_directory
from pyssp_sysml2.roles import (
    is_ssp_model,
    is_study,
    model_usage,
    read_experiment,
    validate_role_markers,
)
from pyssp_sysml2.ssp_metadata import ssp_metadata
from pyssp_sysml2.ssv import write_parameter_set
from pyssp_sysml2.sysml_model import load


@dataclass(frozen=True)
class StudyArtifacts:
    """Paths written by :func:`generate_study`."""

    ssv: Path | None
    ssm: Path | None
    descriptor: Path
    scenario_set: str | None
    model_usage: str


def _relative_name(path: Path, output_dir: Path) -> str:
    return path.relative_to(output_dir).as_posix()


def generate_study(
    architecture_path: Path,
    output_dir: Path,
    composition: str,
    *,
    model_name: str,
    target_ssd: str = "SystemStructure.ssd",
) -> StudyArtifacts:
    """Write ``study.json`` and, for one applied set, its SSV and SSM."""
    architecture = load(architecture_path)
    study = architecture.get_part_def(composition)
    validate_role_markers(architecture)
    if not is_study(architecture, study):
        raise ValueError(
            f"Composition '{composition}' is not marked ':> Study'"
        )

    model_part_usage, model_definition = model_usage(architecture, study)
    if not is_ssp_model(architecture, model_definition):
        raise ValueError(
            f"Study '{composition}' composes '{model_part_usage.type_name}', "
            "which is not marked ':> SspModel'"
        )

    validate_marker_definitions(architecture)
    validate_parameter_dialect(architecture, study)
    sets = parameter_sets_for_generation(architecture, study)
    if len(sets) > 1:
        names = ", ".join(definition.name for definition in sets) or "none"
        raise ValueError(
            f"Study '{composition}' must apply at most one scenario parameter "
            f"set; found {names}"
        )

    model_applications = applied_sets(architecture, model_definition)
    if model_applications and sets:
        raise ValueError(
            f"Study '{composition}' applies a scenario set, but its sut "
            f"'{model_definition.name}' already applies one. A model-owned "
            "scenario is fixed for all studies; remove the study set or move "
            "the scenario to the study."
        )

    experiment = read_experiment(architecture, study)
    model_metadata = ssp_metadata(architecture, model_definition)
    ensure_directory(output_dir)

    set_definition = sets[0] if sets else None
    ssv_path: Path | None = None
    ssm_path: Path | None = None
    scenario: dict[str, str] | None = None
    if set_definition is not None:
        ssv_path = write_parameter_set(
            set_definition, output_dir / f"{set_definition.name}.ssv"
        )

        prefix = f"{model_part_usage.name}."
        ssm_path = output_dir / f"{composition}.ssm"
        with SSM(ssm_path, mode="w") as ssm:
            for spec in mapping_specs(architecture, study):
                for source, target in spec.entries:
                    if not target.startswith(prefix):
                        raise ValueError(
                            f"Study mapping target '{target}' is not below "
                            f"'{model_part_usage.name}'"
                        )
                    ssm.xml.add_mapping(source, target[len(prefix) :])

        scenario = {
            "set": set_definition.name,
            "ssv": _relative_name(ssv_path, output_dir),
            "ssm": _relative_name(ssm_path, output_dir),
        }

    descriptor: dict[str, object] = {
        "model": model_name,
        "composition": model_definition.name,
        "sut": model_part_usage.name,
        "target_ssd": target_ssd,
        "study": composition,
        "experiment": {
            "name": experiment.name,
            "start_time": experiment.start_time,
            "stop_time": experiment.stop_time,
            "step_size": experiment.step_size,
        },
    }
    if scenario is not None:
        descriptor["scenario"] = scenario
    if model_metadata is not None and model_metadata.source is not None:
        descriptor["model_source"] = model_metadata.source
    descriptor_path = output_dir / "study.json"
    descriptor_path.write_text(
        json.dumps(descriptor, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return StudyArtifacts(
        ssv=ssv_path,
        ssm=ssm_path,
        descriptor=descriptor_path,
        scenario_set=set_definition.name if set_definition is not None else None,
        model_usage=model_part_usage.name,
    )
