"""Resolve each parameter binding into sets applied to components.

The binding's prefix, inline or external mapping, and the component
interfaces decide which component a set applies to and which pairs it binds.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pyssp_sysml2.core.control import is_control_attribute
from pyssp_sysml2.model import PortDefinition
from pyssp_sysml2.parameters.dialect.declarations import fixed_count

from .inputs import (
    RESERVED_IDENTIFIERS,
    MappingPair,
    SetApplication,
    _binding_mapping,
    split_indexed,
)


# -- bindings to sets -------------------------------------------------------


def _mapping_pairs(
    entries: Iterable[tuple[str, str]],
    components: set[tuple[str, ...]],
    owner_path: tuple[str, ...] = (),
) -> list[MappingPair]:
    grouped: dict[
        tuple[tuple[str, ...], str, str],
        dict[int | None, int | None],
    ] = {}
    for source, target in entries:
        target_base, target_index = split_indexed(target)
        parts = target_base.split(".")
        if len(parts) < 2:
            raise ValueError(
                f"Parameter mapping target '{target}' must be a hierarchical "
                "component parameter path"
            )
        component_path = tuple(parts[:-1])
        target_member = parts[-1]
        component_name = ".".join(component_path)
        if (
            not component_name
            or not target_member
            or target_member in RESERVED_IDENTIFIERS
        ):
            raise ValueError(
                f"Parameter mapping target '{target}' must be a hierarchical "
                "component parameter path"
            )
        if component_path not in components:
            raise ValueError(
                f"Parameter mapping target '{target}' references unknown component "
                f"'{component_name}'"
            )
        source_base, source_index = split_indexed(source)
        if source_base.startswith(component_name + "."):
            source_base = source_base[len(component_name) + 1 :]
        else:
            relative_name = ".".join(component_path[len(owner_path) :])
            if relative_name and source_base.startswith(relative_name + "."):
                source_base = source_base[len(relative_name) + 1 :]
        if (
            "." in source_base
            or source_base in RESERVED_IDENTIFIERS
            or is_control_attribute(source_base)
        ):
            raise ValueError(
                f"Parameter mapping source '{source}' cannot be represented as a "
                "SysML attribute name"
            )
        if (source_index is None) != (target_index is None):
            raise ValueError(
                f"Parameter mapping '{source}' -> '{target}' must use indices on "
                "both sides or on neither side"
            )
        key = (component_path, source_base, target_member)
        grouped.setdefault(key, {})[source_index] = target_index

    pairs: list[MappingPair] = []
    seen_sources: set[tuple[tuple[str, ...], str]] = set()
    seen_targets: set[tuple[tuple[str, ...], str]] = set()
    for (component_path, source_base, target_member), indices in grouped.items():
        component_name = ".".join(component_path)
        count: int | None = None
        if None in indices:
            if len(indices) > 1:
                raise ValueError(
                    f"Mapping for '{source_base}' mixes scalar and indexed entries"
                )
        else:
            source_indices = sorted(index for index in indices if index is not None)
            target_indices = sorted(
                index for index in indices.values() if index is not None
            )
            if source_indices != target_indices:
                raise ValueError(
                    f"Mapping for '{source_base}' must map matching indices, got "
                    f"{source_indices} -> {target_indices}"
                )
            if source_indices != list(range(len(source_indices))):
                raise ValueError(
                    f"Mapping for '{source_base}' has non-contiguous indices "
                    f"{source_indices}"
                )
            count = len(source_indices)
        source_key = (component_path, source_base)
        target_key = (component_path, target_member)
        if source_key in seen_sources:
            raise ValueError(
                f"Parameter source '{source_base}' maps to more than one target "
                f"for component '{component_name}'"
            )
        if target_key in seen_targets:
            raise ValueError(
                f"Parameter target '{target_member}' is mapped more than once for "
                f"component '{component_name}'"
            )
        seen_sources.add(source_key)
        seen_targets.add(target_key)
        pairs.append(
            MappingPair(component_path, source_base, target_member, count)
        )
    return sorted(
        pairs,
        key=lambda pair: (pair.component_path, pair.source, pair.target),
    )


def _normalize_values(
    values: dict[str, tuple[str, object]], component_path: tuple[str, ...]
) -> dict[str, tuple[str, object]]:
    prefix = ".".join(component_path) + "."
    normalized: dict[str, tuple[str, object]] = {}
    for base, item in values.items():
        if base.startswith(prefix):
            base = base[len(prefix) :]
        if (
            not base
            or "." in base
            or base in RESERVED_IDENTIFIERS
            or is_control_attribute(base)
        ):
            raise ValueError(
                f"Parameter '{base}' cannot be represented as a SysML attribute name"
            )
        normalized[base] = item
    return normalized


def _is_under(path: tuple[str, ...], owner: tuple[str, ...]) -> bool:
    return path[: len(owner)] == owner


def _component_name(path: tuple[str, ...]) -> str:
    return ".".join(path)


def _infer_component(
    values: dict[str, tuple[str, object]],
    components: set[tuple[str, ...]],
    interfaces: dict[tuple[str, ...], PortDefinition | None],
    owner_path: tuple[str, ...] = (),
) -> tuple[str, ...]:
    matches: list[tuple[str, ...]] = []
    for component_path in sorted(components):
        if not _is_under(component_path, owner_path):
            continue
        interface = interfaces.get(component_path)
        if interface is None:
            continue
        try:
            normalized = _normalize_values(values, component_path)
        except ValueError:
            continue
        if set(normalized) <= set(interface.attributes):
            matches.append(component_path)
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError(
            "Cannot infer which component a parameter set applies to; add a "
            "ParameterBinding prefix or ParameterMapping"
        )
    names = ", ".join(".".join(path) for path in matches)
    raise ValueError(
        "Parameter set application is ambiguous between components "
        f"{names}; add a ParameterBinding prefix or ParameterMapping"
    )


def _check_pair_shape(
    pair: MappingPair,
    normalized: dict[str, tuple[str, object]],
    interfaces: dict[tuple[str, ...], PortDefinition | None],
) -> None:
    _, source_value = normalized[pair.source]
    interface = interfaces.get(pair.component_path)
    if interface is None:
        raise ValueError(
            f"SSD applies a parameter set to '{pair.component_name}', but that "
            "component has no parameter connectors"
        )
    target = interface.attributes.get(pair.target)
    if target is None:
        raise ValueError(
            f"Parameter mapping target '{pair.target}' does not exist on "
            f"component '{pair.component_name}'"
        )
    if pair.count is None:
        if isinstance(source_value, tuple):
            raise ValueError(
                f"Mapping source '{pair.source}' is a list but the mapping has "
                "no indices"
            )
        if target.multiplicity:
            raise ValueError(
                f"Mapping target '{pair.target}' declares [{target.multiplicity}] "
                "but the mapping has no indices"
            )
        return

    if not isinstance(source_value, tuple) or len(source_value) != pair.count:
        raise ValueError(
            f"Mapping source '{pair.source}' must contain {pair.count} values"
        )
    if (
        not target.multiplicity
        or fixed_count(target.multiplicity, pair.target) != pair.count
    ):
        raise ValueError(
            f"Mapping target '{pair.target}' must declare [{pair.count}] to match "
            f"the {pair.count} mapped indices"
        )


def _absolute_values(
    values: dict[str, tuple[str, object]], owner_path: tuple[str, ...]
) -> dict[str, tuple[str, object]]:
    """Make parameter-source names absolute relative to the composition root."""
    if not owner_path:
        return values
    absolute: dict[str, tuple[str, object]] = {}
    for base, item in values.items():
        parts = tuple(base.split("."))
        if parts[: len(owner_path)] != owner_path:
            parts = owner_path + parts
        absolute[".".join(parts)] = item
    return absolute


def _absolute_mapping(
    entries: Iterable[tuple[str, str]], owner_path: tuple[str, ...]
) -> list[tuple[str, str]]:
    """Make mapping targets absolute relative to the composition root."""
    result: list[tuple[str, str]] = []
    for source, target in entries:
        target_base, target_index = split_indexed(target)
        parts = tuple(target_base.split("."))
        if owner_path and parts[: len(owner_path)] != owner_path:
            parts = owner_path + parts
        absolute = ".".join(parts)
        if target_index is not None:
            absolute = f"{absolute}[{target_index}]"
        result.append((source, absolute))
    return result


def _effective_prefix(
    binding,
    owner_path: tuple[str, ...],
    *,
    component_level: bool,
) -> tuple[str, ...] | None:
    if not binding.prefix:
        return None
    prefix = binding.prefix.rstrip(".")
    if component_level and prefix in (
        _component_name(owner_path),
        owner_path[-1] if owner_path else "",
    ):
        return owner_path
    return owner_path + tuple(prefix.split("."))


def _applications_for_binding(
    owner_path: tuple[str, ...],
    component_level: bool,
    binding,
    values: dict[str, tuple[str, object]],
    components: set[tuple[str, ...]],
    interfaces: dict[tuple[str, ...], PortDefinition | None],
    ssd_path: Path | None,
) -> list[SetApplication]:
    if not binding.prefix:
        values = _absolute_values(values, owner_path)
    mapping = _binding_mapping(binding, ssd_path)
    if mapping is not None:
        pairs = _mapping_pairs(
            _absolute_mapping(mapping, owner_path),
            components,
            owner_path,
        )
        if not pairs:
            raise ValueError("ParameterBinding contains an empty ParameterMapping")
        by_component: dict[tuple[str, ...], list[MappingPair]] = {}
        for pair in pairs:
            by_component.setdefault(pair.component_path, []).append(pair)
        if component_level and set(by_component) != {owner_path}:
            raise ValueError(
                f"Component-level parameter binding for "
                f"'{_component_name(owner_path)}' maps to components "
                f"{', '.join(_component_name(path) for path in sorted(by_component))}"
            )
        prefix_path = _effective_prefix(
            binding, owner_path, component_level=component_level
        )
        if prefix_path is not None and not all(
            _is_under(path, prefix_path) for path in by_component
        ):
            raise ValueError(
                f"ParameterBinding prefix '{binding.prefix}' conflicts with "
                f"mapping targets "
                f"{', '.join(_component_name(path) for path in sorted(by_component))}"
            )
        outside = [
            path for path in by_component if not _is_under(path, owner_path)
        ]
        if outside:
            raise ValueError(
                f"Parameter binding in '{_component_name(owner_path) or '<root>'}' "
                "maps outside its scope: "
                f"{', '.join(_component_name(path) for path in sorted(outside))}"
            )
        for pair in pairs:
            normalized = _normalize_values(values, pair.component_path)
            if pair.source not in normalized:
                raise ValueError(
                    f"Parameter mapping source '{pair.source}' is not present in "
                    "the parameter set"
                )
            _check_pair_shape(pair, normalized, interfaces)
        return [
            SetApplication(component_path, False, tuple(pairs))
            for component_path, pairs in sorted(by_component.items())
        ]

    prefix_path = _effective_prefix(
        binding, owner_path, component_level=component_level
    )
    if component_level:
        component_path = owner_path
        if prefix_path is not None and prefix_path != owner_path:
            raise ValueError(
                f"Component-level parameter binding for "
                f"'{_component_name(owner_path)}' has conflicting prefix "
                f"'{binding.prefix}'"
            )
    elif prefix_path is not None:
        component_path = prefix_path
        if component_path not in components:
            raise ValueError(
                f"ParameterBinding prefix '{binding.prefix}' references unknown "
                "component"
            )
    else:
        component_path = _infer_component(
            values, components, interfaces, owner_path
        )

    if not _is_under(component_path, owner_path):
        raise ValueError(
            f"Parameter binding in '{_component_name(owner_path) or '<root>'}' "
            f"targets '{_component_name(component_path)}' outside its scope"
        )

    normalized = _normalize_values(values, component_path)
    interface = interfaces.get(component_path)
    if interface is None:
        raise ValueError(
            f"SSD applies a parameter set to "
            f"'{_component_name(component_path)}', but that component has no "
            "parameter connectors"
        )
    missing = sorted(set(normalized) - set(interface.attributes))
    if missing:
        raise ValueError(
            f"Parameter set members {', '.join(missing)} do not exist on "
            f"component '{_component_name(component_path)}'"
        )
    return [SetApplication(component_path, True, ())]
