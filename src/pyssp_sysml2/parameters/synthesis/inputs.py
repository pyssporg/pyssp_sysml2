"""Read SSD, SSV, and SSM inputs into parameter values and mappings.

This layer owns the SSD binding walk, the parameter-set values grouped by base
name, the SSM mapping entries, and the identifiers shared by the other
synthesis modules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pyssp_standard import Component, SSM, SSV, System

from pyssp_sysml2.core.control import (
    CONTROL_PREFIX,
    is_control_attribute,
)
from pyssp_sysml2.model import AttributeDefinition
from pyssp_sysml2.parameters.dialect.declarations import (
    coerce_parameter_value,
)


SSP_TYPES = {"Real", "Integer", "Boolean", "String"}

# SysML keywords that cannot be used as feature/definition names by sysmlpy.
# Parameter names using one of these are rejected rather than emitting a file
# that the loader cannot read back.
RESERVED_IDENTIFIERS = {
    "action",
    "alias",
    "allocate",
    "analysis",
    "attribute",
    "bind",
    "calc",
    "comment",
    "concern",
    "connection",
    "constraint",
    "def",
    "dependency",
    "doc",
    "expose",
    "flow",
    "import",
    "interface",
    "item",
    "metadata",
    "occurrence",
    "package",
    "part",
    "perform",
    "port",
    "ref",
    "rendering",
    "requirement",
    "satisfy",
    "stakeholder",
    "state",
    "typed",
    "verification",
    "view",
    "viewpoint",
}


@dataclass(frozen=True)
class MappingPair:
    component_path: tuple[str, ...]
    source: str
    target: str
    count: int | None = None

    @property
    def component_name(self) -> str:
        return ".".join(self.component_path)


@dataclass(frozen=True)
class SetApplication:
    component_path: tuple[str, ...]
    identity: bool
    pairs: tuple[MappingPair, ...]

    @property
    def component_name(self) -> str:
        return ".".join(self.component_path)


@dataclass
class SetBuild:
    definition: AttributeDefinition
    applications: list[SetApplication]


# -- small parsing helpers --------------------------------------------------


def _identifier(name: str, fallback: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_]", "_", name).strip("_")
    if not cleaned:
        cleaned = fallback
    if cleaned in RESERVED_IDENTIFIERS:
        cleaned = f"p_{cleaned}"
    if cleaned[0].isdigit():
        cleaned = f"_{cleaned}"
    return cleaned


def split_indexed(name: str) -> tuple[str, int | None]:
    """Split ``x[2]`` into ``("x", 2)``; leave scalar names alone."""
    if not name:
        raise ValueError("Parameter name must not be empty")
    if name.endswith("]") and "[" in name:
        base, _, raw_index = name.rpartition("[")
        try:
            index = int(raw_index[:-1])
        except ValueError:
            raise ValueError(f"Unsupported parameter index in '{name}'") from None
        if index < 0:
            raise ValueError(f"Unsupported negative parameter index in '{name}'")
        return base, index
    return name, None


def _ssp_type_name(type_name: str | None) -> str:
    if type_name == "Enumeration":
        return "Integer"
    if type_name in SSP_TYPES:
        return type_name
    return "Real"


def _group_values(
    parameters: Iterable[tuple[str, str | None, object]],
) -> dict[str, tuple[str, object]]:
    """Group SSV parameters into base names with scalar or tuple values."""
    grouped: dict[str, dict[int | None, tuple[str, object]]] = {}
    for name, raw_type, raw_value in parameters:
        base, index = split_indexed(name)
        if not base:
            raise ValueError(f"Parameter '{name}' has an empty base name")
        if is_control_attribute(base):
            raise ValueError(
                f"Parameter '{name}' uses the reserved '{CONTROL_PREFIX}' prefix"
            )
        if base in RESERVED_IDENTIFIERS:
            raise ValueError(
                f"Parameter '{name}' uses reserved SysML keyword '{base}'"
            )
        type_name = _ssp_type_name(raw_type)
        if raw_value is None:
            raise ValueError(f"Parameter '{name}' has no value in the parameter set")
        value = coerce_parameter_value(type_name, raw_value)
        grouped.setdefault(base, {})[index] = (type_name, value)

    result: dict[str, tuple[str, object]] = {}
    for base, by_index in grouped.items():
        if None in by_index:
            if len(by_index) > 1:
                raise ValueError(
                    f"Parameter '{base}' mixes scalar and indexed values"
                )
            result[base] = by_index[None]
            continue
        indices = sorted(index for index in by_index if index is not None)
        if indices != list(range(len(indices))):
            raise ValueError(
                f"Parameter '{base}' has non-contiguous indices {indices}"
            )
        types = {by_index[index][0] for index in indices}
        if len(types) > 1:
            raise ValueError(
                f"Parameter '{base}' mixes types {', '.join(sorted(types))}"
            )
        result[base] = (
            types.pop(),
            tuple(by_index[index][1] for index in indices),
        )
    return result


def _ssv_parameters(parameter_set) -> list[tuple[str, str | None, object]]:
    return [
        (parameter.name, parameter.type_name, parameter.attributes.get("value"))
        for parameter in parameter_set.parameters
    ]


def _resolve_relative(ssd_path: Path | None, source: str) -> Path:
    if ssd_path is None:
        raise ValueError(
            f"Parameter set source '{source}' cannot be resolved without the SSD path"
        )
    path = (ssd_path.parent / source).resolve()
    if not path.is_file():
        raise ValueError(f"Parameter set source not found: {source}")
    return path


def _binding_parameters(
    binding, ssd_path: Path | None
) -> tuple[str, list[tuple[str, str | None, object]]]:
    if binding.parameter_set is not None:
        return (
            binding.parameter_set.name,
            _ssv_parameters(binding.parameter_set),
        )
    if binding.source is None:
        raise ValueError("ParameterBinding has neither inline values nor a source")
    path = _resolve_relative(ssd_path, binding.source)
    with SSV(path, mode="r") as ssv:
        return ssv.xml.name, _ssv_parameters(ssv.xml)


def _mapping_entries(mapping_document) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for mapping in mapping_document.mappings:
        if mapping.transformation is not None:
            raise ValueError("SSM transformations are not supported")
        if mapping.suppress_unit_conversion:
            raise ValueError("SSM unit-conversion suppression is not supported")
        entries.append((mapping.source, mapping.target))
    return entries


def _binding_mapping(
    binding, ssd_path: Path | None
) -> list[tuple[str, str]] | None:
    parameter_mapping = binding.parameter_mapping
    if parameter_mapping is None:
        return None
    if parameter_mapping.mapping is not None:
        return _mapping_entries(parameter_mapping.mapping)
    if parameter_mapping.source is None:
        raise ValueError("ParameterBinding mapping has neither inline mapping nor a source")
    path = _resolve_relative(ssd_path, parameter_mapping.source)
    with SSM(path, mode="r") as ssm:
        return _mapping_entries(ssm.xml)


def _all_bindings(
    ssd_system,
) -> list[tuple[tuple[str, ...], bool, object]]:
    """Every parameter binding with its owner path and component-level flag."""
    bindings: list[tuple[tuple[str, ...], bool, object]] = []

    def walk(system, path: tuple[str, ...]) -> None:
        bindings.extend(
            (path, False, binding) for binding in system.parameter_bindings
        )
        for element in sorted(
            system.elements, key=lambda item: item.name or ""
        ):
            if isinstance(element, Component):
                bindings.extend(
                    (path + (element.name,), True, binding)
                    for binding in element.parameter_bindings
                )
            elif isinstance(element, System):
                walk(element, path + (element.name,))

    walk(ssd_system, ())
    return bindings


def _component_map(
    ssd_system,
) -> dict[tuple[str, ...], Component | System]:
    """Every parameterable component or system, keyed by its nested path."""
    components: dict[tuple[str, ...], Component | System] = {}

    def walk(system, path: tuple[str, ...]) -> None:
        for element in sorted(
            system.elements, key=lambda item: item.name or ""
        ):
            if not element.name:
                continue
            element_path = path + (element.name,)
            components[element_path] = element
            if isinstance(element, System):
                walk(element, element_path)

    walk(ssd_system, ())
    return components
