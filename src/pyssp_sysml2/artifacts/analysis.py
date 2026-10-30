"""Generate analysis artifacts from a SysML ``Analysis`` composition.

An analysis composes one ``SspModel`` usage (conventionally ``sut``), applies
zero or one scenario parameter set, and declares one experiment. Generation
writes an ``analysis.json`` descriptor and, when a set is applied, an SSV plus
one SSM with targets relative to the exported model root. An analysis without a
set yields an experiment-only descriptor for a model body that stays a
checked-in SSP; that body is named by the model's ``ssp_meta.source`` and
recorded as ``model_source``. It never writes an SSD or an SSP.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from pyssp_standard import SSM

from pyssp_sysml2.parameters.dialect.composition import (
    applied_sets,
    validate_parameter_dialect,
)
from pyssp_sysml2.parameters.dialect.mapping import (
    mapping_specs,
    parameter_sets_for_generation,
)
from pyssp_sysml2.parameters.dialect.markers import validate_marker_definitions
from pyssp_sysml2.core.paths import ensure_directory
from pyssp_sysml2.metadata.roles import (
    is_ssp_model,
    is_analysis,
    model_usage,
    read_experiment,
    validate_role_markers,
)
from pyssp_sysml2.metadata.ssp_metadata import ssp_metadata
from pyssp_sysml2.artifacts.ssv import write_parameter_set
from pyssp_sysml2.model import load
from pyssp_sysml2.parameters.constraints import enforce_constraints
from pyssp_sysml2.parameters.selection import analysis_selection
from pyssp_sysml2.parameters.variation import resolve_selected


@dataclass(frozen=True)
class AnalysisArtifacts:
    """Paths written by :func:`generate_analysis`."""

    ssv: Path | None
    ssm: Path | None
    descriptor: Path
    scenario_set: str | None
    model_usage: str


def _relative_name(path: Path, output_dir: Path) -> str:
    return path.relative_to(output_dir).as_posix()


def generate_analysis(
    architecture_path: Path,
    output_dir: Path,
    composition: str,
    *,
    model_name: str,
    target_ssd: str = "SystemStructure.ssd",
    selections: Mapping[str, str] | None = None,
) -> AnalysisArtifacts:
    """Write ``analysis.json`` and, for one applied set, its SSV and SSM.

    ``selections`` resolves variation points in the analysis before generation;
    see :func:`pyssp_sysml2.parameters.variation.resolve`. When it is ``None``,
    the analysis's authored ``pyssp_selection`` is used. An explicit map wins,
    so a caller can still force an illegal combination and have the constraints
    reject it. An analysis that carries an unselected variation point fails
    instead of emitting a flat scenario.
    """
    architecture = load(architecture_path)
    if selections is None:
        selections = analysis_selection(architecture, composition)
    architecture, canonical = resolve_selected(
        architecture, composition, selections or {}
    )
    enforce_constraints(architecture, composition, canonical)
    analysis = architecture.get_part_def(composition)
    validate_role_markers(architecture)
    if not is_analysis(architecture, analysis):
        raise ValueError(
            f"Composition '{composition}' is not marked ':> Analysis'"
        )

    model_part_usage, model_definition = model_usage(architecture, analysis)
    if not is_ssp_model(architecture, model_definition):
        raise ValueError(
            f"Analysis '{composition}' composes '{model_part_usage.type_name}', "
            "which is not marked ':> SspModel'"
        )

    validate_marker_definitions(architecture)
    validate_parameter_dialect(architecture, analysis)
    sets = parameter_sets_for_generation(architecture, analysis)
    if len(sets) > 1:
        names = ", ".join(definition.name for definition in sets) or "none"
        raise ValueError(
            f"Analysis '{composition}' must apply at most one scenario parameter "
            f"set; found {names}"
        )

    model_applications = applied_sets(architecture, model_definition)
    if model_applications and sets:
        raise ValueError(
            f"Analysis '{composition}' applies a scenario set, but its sut "
            f"'{model_definition.name}' already applies one. A model-owned "
            "scenario is fixed for all analyses; remove the analysis set or move "
            "the scenario to the analysis."
        )

    experiment = read_experiment(architecture, analysis)
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
            for spec in mapping_specs(architecture, analysis):
                for source, target in spec.entries:
                    if not target.startswith(prefix):
                        raise ValueError(
                            f"Analysis mapping target '{target}' is not below "
                            f"'{model_part_usage.name}'"
                        )
                    ssm.add_mapping(source, target[len(prefix) :])

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
        "analysis": composition,
        "experiment": {
            "name": experiment.name,
            "start_time": experiment.start_time,
            "stop_time": experiment.stop_time,
            "step_size": experiment.step_size,
        },
    }
    if analysis.doc:
        descriptor["description"] = analysis.doc
    if scenario is not None:
        descriptor["scenario"] = scenario
    if model_metadata is not None and model_metadata.source is not None:
        descriptor["model_source"] = model_metadata.source
    descriptor_path = output_dir / "analysis.json"
    descriptor_path.write_text(
        json.dumps(descriptor, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return AnalysisArtifacts(
        ssv=ssv_path,
        ssm=ssm_path,
        descriptor=descriptor_path,
        scenario_set=set_definition.name if set_definition is not None else None,
        model_usage=model_part_usage.name,
    )
