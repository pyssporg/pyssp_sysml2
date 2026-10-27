"""SSP archive packaging from a SysML architecture.

``generate ssp`` closes the loop between the SysML model and a runnable SSP:

* the SSD is generated from SysML,
* every leaf component's built FMU is read from ``fmu_meta.source`` and added
  under ``resources/``,
* applied parameter sets are written as SSVs under the prefix referenced by
  the SSD parameter bindings.

The archive uses FMI-style fixed timestamps, so repeated runs with unchanged
inputs produce byte-identical ``.ssp`` archives.
"""

from __future__ import annotations

import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from pyssp_standard import (
    Component,
    FMU,
    SSD,
    SSP,
    System,
    copy_resource_directory,
    validate_component_fmu,
)

from pyssp_sysml2.fmi_helpers import fmu_filename
from pyssp_sysml2.fmu_metadata import fmu_metadata
from pyssp_sysml2.parameters import (
    component_definitions,
    parameter_set_resource,
    parameter_sets_for_generation,
    validate_parameter_dialect,
)
from pyssp_sysml2.paths import ensure_parent_dir
from pyssp_sysml2.roles import is_study, validate_role_markers
from pyssp_sysml2.ssd import build_ssd
from pyssp_sysml2.ssp_metadata import ssp_metadata
from pyssp_sysml2.ssv import write_parameter_set
from pyssp_sysml2.sysml_model import Architecture, PartDefinition, load

DEFAULT_PARAMETER_SET_PREFIX = "resources/parameter_sets"


@dataclass(frozen=True)
class _FmuResource:
    part_def: PartDefinition
    source: Path | None
    resource_name: str


def _resolve_fmu_source(source: str, fmu_root: Path | None) -> Path:
    path = Path(source).expanduser()
    if not path.is_absolute():
        path = (fmu_root or Path.cwd()) / path
    return path.resolve()


def _collect_fmu_resources(
    architecture: Architecture,
    system: PartDefinition,
    fmu_root: Path | None,
    *,
    allow_missing: bool = False,
) -> list[_FmuResource]:
    resources: list[_FmuResource] = []
    for part_def in component_definitions(architecture, system):
        if part_def.parts:
            continue

        metadata = fmu_metadata(architecture, part_def)
        resource_name = fmu_filename(part_def.name)
        if metadata is None or not metadata.source:
            # No FMU authored yet: the design structure leaves the component
            # unpopulated (empty SSD source).
            resources.append(_FmuResource(part_def, None, resource_name))
            continue

        source = _resolve_fmu_source(metadata.source, fmu_root)
        if not source.exists():
            if not allow_missing:
                raise FileNotFoundError(
                    f"FMU source for {part_def.name} does not exist: {source}"
                )
            resources.append(_FmuResource(part_def, None, resource_name))
            continue
        if source.is_file() and source.suffix.lower() != ".fmu":
            raise ValueError(
                f"FMU source for {part_def.name} must be a .fmu file or an "
                f"extracted FMU directory, got: {source}"
            )
        if source.is_dir() and not (source / "modelDescription.xml").is_file():
            raise FileNotFoundError(
                "FMU directory does not contain modelDescription.xml: "
                f"{source}"
            )

        resources.append(
            _FmuResource(
                part_def=part_def,
                source=source,
                resource_name=resource_name,
            )
        )
    return resources


def _iter_components(system: System):
    for element in system.elements:
        if isinstance(element, System):
            yield from _iter_components(element)
        elif isinstance(element, Component):
            yield element


def _validate_ssd_components(
    system: System,
    resources: dict[str, Path | None],
) -> None:
    resources_by_source = {
        f"resources/{resource_name}": source
        for resource_name, source in resources.items()
    }
    model_descriptions: dict[Path, object] = {}

    for component in _iter_components(system):
        if not component.source:
            # Design-first export: the component has no FMU yet.
            continue
        if component.source not in resources_by_source:
            raise ValueError(
                f"SSD component '{component.name}' references unknown FMU "
                f"resource '{component.source}'"
            )
        source = resources_by_source[component.source]
        if source is None:
            # Design-first export: the resource is intentionally not packaged.
            continue
        if source not in model_descriptions:
            with FMU(source, mode="r") as fmu:
                with fmu.model_description as md:
                    model_descriptions[source] = md.xml
        validate_component_fmu(
            component,
            model_descriptions[source],
            source=str(source),
        )


def _unique_resources(resources: list[_FmuResource]) -> dict[str, Path | None]:
    unique: dict[str, Path | None] = {}
    for resource in resources:
        if (
            resource.resource_name in unique
            and unique[resource.resource_name] != resource.source
        ):
            raise ValueError(
                f"FMU resource name '{resource.resource_name}' is used by "
                f"{resource.part_def.name} and another part definition with a "
                "different source"
            )
        unique[resource.resource_name] = resource.source
    return unique


def _add_fmu_resource(
    archive: SSP, source: Path, resource_name: str
) -> None:
    if source.is_dir():
        copy_resource_directory(
            source,
            archive.runtime.resolve("resources"),
            resource_name,
        )
    else:
        archive.runtime.add_file(source, target_name=f"resources/{resource_name}")


def _normalise_parameter_set_prefix(prefix: str) -> str:
    cleaned = str(prefix).strip().strip("/")
    if not cleaned:
        return ""
    if "\\" in cleaned:
        raise ValueError(
            "parameter_set_prefix must use '/' separators inside the archive"
        )
    path = PurePosixPath(cleaned)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(
            "parameter_set_prefix must be a relative archive path without '..'"
        )
    return path.as_posix()


def generate_ssp(
    architecture_path: Path,
    output_path: Path,
    composition: str,
    *,
    parameter_set_prefix: str = DEFAULT_PARAMETER_SET_PREFIX,
    fmu_root: Path | None = None,
    type_check: bool = True,
    validate_fmus: bool = True,
    allow_missing_fmus: bool = False,
) -> Path:
    """Build an ``.ssp`` archive from a SysML architecture and its built FMUs.

    Relative ``fmu_meta.source`` paths are resolved against ``fmu_root`` (the
    current working directory when omitted). ``SSD`` parameter bindings and
    packaged SSVs share ``parameter_set_prefix``.

    When ``validate_fmus`` is true (the default), each FMU's
    ``modelDescription.xml`` is checked against the generated SSD connector
    names and the requested ``fmu_meta.implementation``.

    A leaf component without ``fmu_meta.source`` has no FMU yet: it is exported
    with an empty SSD ``source`` and no resource. The archive is then a design
    artifact until the FMUs are attached with ``SSP.attach_fmu``.

    When ``allow_missing_fmus`` is true, a component whose declared
    ``fmu_meta.source`` does not exist on disk is exported the same way, with
    its expected ``resources/<name>`` source and no packaged FMU. Without the
    flag, a missing declared source is an error.
    """
    parameter_set_prefix = _normalise_parameter_set_prefix(parameter_set_prefix)
    architecture = load(architecture_path)
    system = architecture.get_part_def(composition)
    validate_role_markers(architecture)
    if is_study(architecture, system):
        raise ValueError(
            f"Composition '{composition}' is a Study; studies are not "
            "exportable as SSPs. Export its 'part sut : <SspModel>' model "
            "instead."
        )
    if ssp_metadata(architecture, system) is not None:
        raise ValueError(
            f"Composition '{composition}' selects an external SSP source via "
            "'ssp_meta'; it is a study-only boundary and cannot be exported. "
            "Generate its study instead."
        )
    validate_parameter_dialect(architecture, system)

    fmu_resources = _collect_fmu_resources(
        architecture, system, fmu_root, allow_missing=allow_missing_fmus
    )
    for resource in fmu_resources:
        if resource.source is None:
            warnings.warn(
                f"{resource.part_def.name}: FMU source is missing; the "
                "component is exported without its FMU (design structure)",
                stacklevel=2,
            )
    set_definitions = parameter_sets_for_generation(architecture, system)
    unique_resources = _unique_resources(fmu_resources)

    ensure_parent_dir(output_path)

    with tempfile.TemporaryDirectory(prefix="pyssp_ssp_") as temp_dir:
        temp_path = Path(temp_dir)
        ssd_path = temp_path / "SystemStructure.ssd"
        with SSD(ssd_path, mode="w") as ssd:
            build_ssd(
                ssd,
                system,
                architecture,
                type_check,
                parameter_set_prefix=parameter_set_prefix,
            )
            if validate_fmus:
                assert ssd.system is not None
                _validate_ssd_components(ssd.system, unique_resources)

        ssv_paths = []
        for definition in set_definitions:
            ssv_path = write_parameter_set(
                definition, temp_path / f"{definition.name}.ssv"
            )
            ssv_paths.append((definition, ssv_path))

        with SSP(output_path, mode="w") as archive:
            archive.runtime.add_file(ssd_path, target_name="SystemStructure.ssd")
            for resource_name, source in sorted(unique_resources.items()):
                if source is None:
                    continue
                _add_fmu_resource(archive, source, resource_name)
            for definition, ssv_path in ssv_paths:
                archive.runtime.add_file(
                    ssv_path,
                    target_name=parameter_set_resource(
                        parameter_set_prefix, definition.name
                    ),
                )

    return output_path
