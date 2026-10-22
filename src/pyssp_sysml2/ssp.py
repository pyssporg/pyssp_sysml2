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
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from pyssp_standard.common.archive import copy_resource_directory
from pyssp_standard.fmu import FMU
from pyssp_standard.ssd import SSD
from pyssp_standard.ssp import SSP
from pyssp_standard.standard.ssp1.model.ssd_model import Ssd1Component, Ssd1System

from pyssp_sysml2.fmi_helpers import fmu_resource_path
from pyssp_sysml2.fmu_metadata import fmu_metadata
from pyssp_sysml2.parameters import (
    component_definitions,
    parameter_sets_for_generation,
    validate_parameter_dialect,
)
from pyssp_sysml2.paths import ensure_parent_dir
from pyssp_sysml2.roles import is_study, validate_role_markers
from pyssp_sysml2.ssd import build_ssd
from pyssp_sysml2.ssv import write_parameter_set
from pyssp_sysml2.sysml_model import Architecture, PartDefinition, load

DEFAULT_PARAMETER_SET_PREFIX = "resources/parameter_sets"


@dataclass(frozen=True)
class _FmuResource:
    part_def: PartDefinition
    source: Path
    resource_name: str


def _resolve_fmu_source(source: str, fmu_root: Path | None) -> Path:
    path = Path(source).expanduser()
    if not path.is_absolute():
        path = (fmu_root or Path.cwd()) / path
    return path.resolve()


def _default_resource_name(part_def: PartDefinition) -> str:
    return Path(fmu_resource_path(part_def.name)).name


def _collect_fmu_resources(
    architecture: Architecture,
    system: PartDefinition,
    fmu_root: Path | None,
) -> list[_FmuResource]:
    resources: list[_FmuResource] = []
    for part_def in component_definitions(architecture, system):
        if part_def.parts:
            continue

        metadata = fmu_metadata(architecture, part_def)
        if metadata is None or not metadata.source:
            raise ValueError(
                f"{part_def.name} has no fmu_meta.source; generate ssp requires "
                "the built FMU path in typed FMU metadata"
            )

        source = _resolve_fmu_source(metadata.source, fmu_root)
        if not source.exists():
            raise FileNotFoundError(
                f"FMU source for {part_def.name} does not exist: {source}"
            )
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
                resource_name=(
                    metadata.resource_name or _default_resource_name(part_def)
                ),
            )
        )
    return resources


def _interface_types(model_description) -> set[str]:
    interface_type = getattr(model_description, "interface_type", None)
    if interface_type:
        return {interface_type}

    # FMI 3 describes the supported interfaces with child elements instead of
    # a single interfaceType attribute.
    interfaces: set[str] = set()
    if getattr(model_description, "co_simulation", None) is not None:
        interfaces.add("CoSimulation")
    if getattr(model_description, "model_exchange", None) is not None:
        interfaces.add("ModelExchange")
    if getattr(model_description, "scheduled_execution", None) is not None:
        interfaces.add("ScheduledExecution")
    return interfaces


def _open_fmu(source: Path) -> tuple[set[str], set[str]]:
    with FMU(source, mode="r") as fmu:
        with fmu.model_description as model_description:
            names = {variable.name for variable in model_description.xml.variables}
            interfaces = _interface_types(model_description.xml)
    return names, interfaces


def _iter_components(system: Ssd1System):
    for element in system.elements:
        if isinstance(element, Ssd1System):
            yield from _iter_components(element)
        elif isinstance(element, Ssd1Component):
            yield element


def _validate_ssd_components(
    system: Ssd1System,
    resources: dict[str, Path],
) -> None:
    resources_by_source = {
        f"resources/{resource_name}": source
        for resource_name, source in resources.items()
    }
    fmu_info: dict[Path, tuple[set[str], set[str]]] = {}

    for component in _iter_components(system):
        source = resources_by_source.get(component.source)
        if source is None:
            raise ValueError(
                f"SSD component '{component.name}' references unknown FMU "
                f"resource '{component.source}'"
            )
        if source not in fmu_info:
            fmu_info[source] = _open_fmu(source)
        variable_names, interface_types = fmu_info[source]

        expected_names = {connector.name for connector in component.connectors}
        missing = sorted(expected_names - variable_names)
        if missing:
            preview = ", ".join(missing[:8])
            if len(missing) > 8:
                preview = f"{preview}, ..."
            raise ValueError(
                f"{component.name}: FMU {source} is missing variable(s) used "
                f"by the SSD: {preview}. SSD connector names must match the "
                "FMU modelDescription; rename the SysML ports/parameters or "
                "the FMU variables, or skip FMU validation."
            )

        implementation = component.implementation
        if (
            implementation
            and interface_types
            and implementation.lower()
            not in {item.lower() for item in interface_types}
        ):
            exposed = ", ".join(sorted(interface_types))
            raise ValueError(
                f"{component.name}: component implementation is "
                f"'{implementation}', but {source} exposes '{exposed}'"
            )


def _unique_resources(resources: list[_FmuResource]) -> dict[str, Path]:
    unique: dict[str, Path] = {}
    for resource in resources:
        existing = unique.get(resource.resource_name)
        if existing is not None and existing != resource.source:
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


def _parameter_set_target(prefix: str, set_name: str) -> str:
    return f"{prefix}/{set_name}.ssv" if prefix else f"{set_name}.ssv"


def generate_ssp(
    architecture_path: Path,
    output_path: Path,
    composition: str,
    *,
    parameter_set_prefix: str = DEFAULT_PARAMETER_SET_PREFIX,
    fmu_root: Path | None = None,
    type_check: bool = True,
    validate_fmus: bool = True,
) -> Path:
    """Build an ``.ssp`` archive from a SysML architecture and its built FMUs.

    Relative ``fmu_meta.source`` paths are resolved against ``fmu_root`` (the
    current working directory when omitted). ``SSD`` parameter bindings and
    packaged SSVs share ``parameter_set_prefix``.

    When ``validate_fmus`` is true (the default), each FMU's
    ``modelDescription.xml`` is checked against the generated SSD connector
    names and the requested ``fmu_meta.implementation``.
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
    validate_parameter_dialect(architecture, system)

    fmu_resources = _collect_fmu_resources(architecture, system, fmu_root)
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
                assert ssd.xml.system is not None
                _validate_ssd_components(ssd.xml.system, unique_resources)

        ssv_paths = []
        for definition in set_definitions:
            ssv_path = write_parameter_set(
                definition, temp_path / f"{definition.name}.ssv"
            )
            ssv_paths.append((definition, ssv_path))

        with SSP(output_path, mode="w") as archive:
            archive.runtime.add_file(ssd_path, target_name="SystemStructure.ssd")
            for resource_name, source in sorted(unique_resources.items()):
                _add_fmu_resource(archive, source, resource_name)
            for definition, ssv_path in ssv_paths:
                archive.runtime.add_file(
                    ssv_path,
                    target_name=_parameter_set_target(
                        parameter_set_prefix, definition.name
                    ),
                )

    return output_path
