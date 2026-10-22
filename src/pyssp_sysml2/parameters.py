"""Parameter interfaces, parameter sets, and SSP mapping helpers.

The dialect this module implements:

- a **parameter interface** is an ``attribute def`` marked ``:>
  ParameterInterface``;
- a parameter **set** is an ``attribute def`` marked ``:> ParameterSet``;
- a component exposes an interface through a single fixed-name bag,
  ``attribute parameters : <Interface>;``;
- a composition applies one set per component usage with ``bind``: either a
  whole-object bind (identity mapping) or one bind per member (explicit
  mapping).

Everything here works against the repo-owned model; generators only consume
the helpers in this module.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

from pyssp_sysml2.control import is_control_attribute
from pyssp_sysml2.sysml_model import (
    Architecture,
    Attribute,
    AttributeDefinition,
    Binding,
    PartDefinition,
    PartUsage,
    load,
)

PARAMETERS_BAG_NAME = "parameters"

# Marker definitions the dialect relies on. Models declare them as ordinary
# (empty) attribute definitions; the last qualified-name segment is matched so
# ``Pyssp::ParameterSet`` works as well as the bare name.
PARAMETER_INTERFACE_MARKER = "ParameterInterface"
PARAMETER_SET_MARKER = "ParameterSet"


# -- role predicates --------------------------------------------------------


def _specializes_marker(
    definition: AttributeDefinition | None, marker: str
) -> bool:
    if definition is None:
        return False
    return any(
        name.split("::")[-1] == marker for name in definition.specializes
    )


def is_parameter_interface(definition: AttributeDefinition | None) -> bool:
    """True when ``definition`` is marked ``:> ParameterInterface``."""
    return _specializes_marker(definition, PARAMETER_INTERFACE_MARKER)


def is_parameter_set(definition: AttributeDefinition | None) -> bool:
    """True when ``definition`` is marked ``:> ParameterSet``."""
    return _specializes_marker(definition, PARAMETER_SET_MARKER)


def validate_marker_definitions(architecture: Architecture) -> None:
    """Require the marker defs used by ``:>`` to exist in the package."""
    used = {
        name.split("::")[-1]
        for definition in architecture.attribute_definitions.values()
        for name in definition.specializes
        if name.split("::")[-1]
        in (PARAMETER_INTERFACE_MARKER, PARAMETER_SET_MARKER)
    }
    defined = {
        name.split("::")[-1] for name in architecture.attribute_definitions
    }
    missing = sorted(used - defined)
    if missing:
        definitions = ", ".join(
            f"attribute def {marker};" for marker in missing
        )
        raise ValueError(
            "Parameter-set dialect uses missing marker definition(s) "
            f"{', '.join(missing)}. Add {definitions} to the package."
        )


# -- interface and declaration resolution -----------------------------------


def parameter_bag(
    architecture: Architecture, part_def: PartDefinition
) -> Attribute | None:
    """The ``parameters`` bag of a part def, when its type is an attribute def."""
    bag = part_def.attributes.get(PARAMETERS_BAG_NAME)
    if bag is None or architecture.resolve_attribute_def(bag) is None:
        return None
    return bag


def parameter_interface(
    architecture: Architecture, part_def: PartDefinition
) -> AttributeDefinition | None:
    """Resolve and validate the parameter interface of a part def.

    ``None`` means the part uses the legacy flat-attribute dialect. A
    ``parameters`` bag typed by an unmarked attribute def is an error: the
    dialect requires the marker so role confusion is caught early.
    """
    bag = parameter_bag(architecture, part_def)
    if bag is None:
        return None
    definition = architecture.resolve_attribute_def(bag)
    assert definition is not None  # parameter_bag already resolved it
    if not is_parameter_interface(definition):
        raise ValueError(
            f"Parameter bag {part_def.name}.{PARAMETERS_BAG_NAME} is typed by "
            f"'{definition.name}', which is not marked ':> {PARAMETER_INTERFACE_MARKER}'"
        )
    return definition


def parameter_declarations(
    architecture: Architecture, part_def: PartDefinition
) -> list[Attribute]:
    """Ordered parameter declarations for a component.

    New dialect: the members of the part's parameter interface. Legacy
    dialect: the part's own non-control attributes. Mixing a parameter bag
    with flat parameter attributes is rejected so the two dialects never blur.
    """
    interface = parameter_interface(architecture, part_def)
    if interface is not None:
        flat = [
            name
            for name in part_def.attributes
            if name != PARAMETERS_BAG_NAME and not is_control_attribute(name)
        ]
        if flat:
            raise ValueError(
                f"{part_def.name} mixes a '{PARAMETERS_BAG_NAME}' bag with flat "
                f"parameter attributes: {', '.join(sorted(flat))}"
            )
        return [
            attribute
            for name, attribute in interface.attributes.items()
            if not is_control_attribute(name)
        ]

    return [
        attribute
        for name, attribute in part_def.attributes.items()
        if not is_control_attribute(name)
    ]


# -- applied sets -----------------------------------------------------------


@dataclass(frozen=True)
class AppliedSet:
    """One composition usage applying a set to one component usage."""

    usage_name: str
    set_definition: AttributeDefinition
    part_usage: PartUsage
    bindings: tuple[Binding, ...]
    identity: bool


@dataclass(frozen=True)
class MappingSpec:
    """Mapping entries for one (set, component usage) application."""

    set_name: str
    set_usage: str
    part_name: str
    identity: bool
    entries: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ParameterItem:
    """One SSP-level parameter after expanding a declared multiplicity."""

    name: str
    type_name: str
    value: object = None


def parameter_items(attribute: Attribute) -> list[ParameterItem]:
    """Expand an attribute's multiplicity/list value into SSP parameter items.

    Interfaces use the declared multiplicity (``Real[3]``) even without a
    value; legacy tuple values expand element-wise. The value is the declared
    default when present, otherwise ``None``.
    """
    type_name = attribute.primitive_type_str()
    if attribute.multiplicity:
        count = fixed_count(attribute.multiplicity, attribute.name)
        value = attribute.value
        if value is None:
            values: tuple = (None,) * count
        elif not isinstance(value, tuple):
            raise ValueError(
                f"Parameter '{attribute.name}' must provide {count} values for "
                f"[{attribute.multiplicity}], got a scalar"
            )
        elif len(value) != count:
            raise ValueError(
                f"Parameter '{attribute.name}' provides {len(value)} values but "
                f"declares [{attribute.multiplicity}]"
            )
        else:
            values = value
        return [
            ParameterItem(
                name=f"{attribute.name}[{index}]",
                type_name=type_name,
                value=values[index],
            )
            for index in range(count)
        ]

    if attribute.is_list:
        return [
            ParameterItem(
                name=f"{attribute.name}[{index}]",
                type_name=type_name,
                value=value,
            )
            for index, value in enumerate(attribute.value)
        ]

    return [
        ParameterItem(
            name=attribute.name,
            type_name=type_name,
            value=attribute.value,
        )
    ]


def coerce_parameter_value(type_name: str, value: object) -> object:
    """Coerce an SSV literal to the Python type used in SysML attributes."""
    if value is None:
        return None
    if type_name == "Real":
        return float(value)
    if type_name == "Integer":
        return int(value)
    if type_name == "Boolean":
        return str(value).lower() == "true"
    return str(value)


def has_parameter_dialect(
    architecture: Architecture, system: PartDefinition
) -> bool:
    """True when a composition uses parameter interfaces/sets or bindings."""
    if set_usages(architecture, system):
        return True
    if any(
        len(binding.target) >= 2
        and binding.target[1] == PARAMETERS_BAG_NAME
        for binding in system.bindings
    ):
        return True
    for usage in system.parts.values():
        part_def = architecture.resolve_part(usage)
        if part_def is not None and parameter_bag(architecture, part_def) is not None:
            return True
    return False


def set_usages(
    architecture: Architecture, system: PartDefinition
) -> dict[str, Attribute]:
    """Composition attributes whose type is marked ``ParameterSet``."""
    usages: dict[str, Attribute] = {}
    for name, attribute in system.attributes.items():
        if is_control_attribute(name):
            continue
        definition = architecture.resolve_attribute_def(attribute)
        if is_parameter_set(definition):
            usages[name] = attribute
    return usages


def _binding_kind(binding: Binding, part_name: str) -> str | None:
    """Classify a binding target as ``"identity"``, ``"member"``, or None."""
    target = binding.target
    if len(target) < 2 or target[0] != part_name:
        return None
    if target[1] != PARAMETERS_BAG_NAME:
        return None
    if len(target) == 2:
        return "identity"
    if len(target) == 3:
        return "member"
    raise ValueError(
        "Parameter bindings must target '<component>.parameters' or "
        f"'<component>.parameters.<member>', got '{'.'.join(target)}'"
    )


def applied_set(
    architecture: Architecture, system: PartDefinition, part_usage: PartUsage
) -> AppliedSet | None:
    """The single set applied to ``part_usage``, or None when unbound."""
    part_name = part_usage.name
    bindings: list[Binding] = []
    kinds: set[str] = set()
    for binding in system.bindings:
        kind = _binding_kind(binding, part_name)
        if kind is None:
            continue
        if not binding.source:
            raise ValueError(f"Binding '{binding.key}' has no source feature")
        bindings.append(binding)
        kinds.add(kind)

    if not bindings:
        return None
    if len(kinds) > 1:
        raise ValueError(
            f"{part_name} mixes whole-object and per-member parameter bindings; "
            "use one form per component usage"
        )

    usage_names = {binding.source[0] for binding in bindings}
    if len(usage_names) > 1:
        raise ValueError(
            f"Multiple parameter sets are applied to {part_name}: "
            f"{', '.join(sorted(usage_names))}. Only one effective set is supported."
        )
    usage_name = usage_names.pop()

    usage = system.attributes.get(usage_name)
    if usage is None:
        raise ValueError(
            f"Binding for {part_name} references '{usage_name}', "
            "which is not a composition attribute"
        )
    definition = architecture.resolve_attribute_def(usage)
    if definition is None:
        raise ValueError(
            f"Parameter set usage '{usage_name}' is typed by "
            f"'{usage.type_name}', which is not a known attribute definition"
        )
    if not is_parameter_set(definition):
        raise ValueError(
            f"Parameter set usage '{usage_name}' is typed by '{definition.name}', "
            f"which is not marked ':> {PARAMETER_SET_MARKER}'"
        )

    for binding in bindings:
        if len(binding.source) not in (1, 2):
            raise ValueError(
                "Parameter binding sources must be '<set>.member' or '<set>', "
                f"got '{'.'.join(binding.source)}'"
            )
        kind = _binding_kind(binding, part_name)
        if kind == "identity" and len(binding.source) != 1:
            raise ValueError(
                "A whole-object parameter binding must reference a set usage, "
                f"not '{'.'.join(binding.source)}'"
            )
        if kind == "member" and len(binding.source) != 2:
            raise ValueError(
                "A per-member parameter binding must reference '<set>.<member>', "
                f"got '{'.'.join(binding.source)}'"
            )

    return AppliedSet(
        usage_name=usage_name,
        set_definition=definition,
        part_usage=part_usage,
        bindings=tuple(bindings),
        identity=("identity" in kinds),
    )


def applied_sets(
    architecture: Architecture, system: PartDefinition
) -> list[AppliedSet]:
    """Every component usage in ``system`` with an applied parameter set."""
    applied: list[AppliedSet] = []
    for part_usage in system.parts.values():
        application = applied_set(architecture, system, part_usage)
        if application is not None:
            applied.append(application)
    return applied


# -- mapping ----------------------------------------------------------------


def fixed_count(multiplicity: str, name: str) -> int:
    """Number of elements for a fixed multiplicity, or error when variable."""
    if multiplicity == "*" or multiplicity.endswith("..*"):
        raise ValueError(
            f"Parameter '{name}' has unbounded multiplicity '[{multiplicity}]'; "
            "SSP parameters need a fixed length"
        )
    if ".." in multiplicity:
        lower, upper = multiplicity.split("..", 1)
        if lower != upper:
            raise ValueError(
                f"Parameter '{name}' has variable multiplicity '[{multiplicity}]'; "
                "SSP parameters need a fixed length"
            )
        multiplicity = lower
    try:
        return int(multiplicity)
    except ValueError:
        raise ValueError(
            f"Parameter '{name}' has unsupported multiplicity '[{multiplicity}]'"
        ) from None


def _expand_entries(
    source_name: str,
    target_name: str,
    source: Attribute,
    target: Attribute,
) -> list[tuple[str, str]]:
    """Source/target pairs for one mapped member, expanding fixed-length lists."""
    if source.value is None:
        raise ValueError(
            f"Parameter set member '{source_name}' has no value but is bound to "
            f"'{target_name}'"
        )
    if target.multiplicity:
        count = fixed_count(target.multiplicity, target_name)
        if not isinstance(source.value, tuple):
            raise ValueError(
                f"'{source_name}' must provide {count} values for list parameter "
                f"'{target_name}', got a scalar"
            )
        if len(source.value) != count:
            raise ValueError(
                f"'{source_name}' provides {len(source.value)} values but "
                f"'{target_name}' declares [{target.multiplicity}]"
            )
        return [
            (f"{source_name}[{index}]", f"{target_name}[{index}]")
            for index in range(count)
        ]
    if isinstance(source.value, tuple):
        raise ValueError(
            f"'{source_name}' is list-valued but target parameter '{target_name}' "
            "does not declare a multiplicity"
        )
    return [(source_name, target_name)]


def _member_type_error(
    source: Attribute, target: Attribute, source_name: str, target_name: str
) -> None:
    source_type = source.primitive_type_str()
    target_type = target.primitive_type_str()
    if source_type != target_type:
        raise ValueError(
            f"Parameter mapping '{source_name}' -> '{target_name}' has incompatible "
            f"types: {source_type} vs {target_type}"
        )


def _identity_entries(
    application: AppliedSet, interface: AttributeDefinition, part_name: str
) -> list[tuple[str, str]]:
    """Expand a whole-object bind into identity mappings."""
    set_members = application.set_definition.attributes
    mapped: set[str] = set()
    entries: list[tuple[str, str]] = []
    for member_name, target in interface.attributes.items():
        if is_control_attribute(member_name):
            continue
        source = set_members.get(member_name)
        if source is None:
            continue
        _member_type_error(
            source, target, member_name, f"{part_name}.{member_name}"
        )
        entries.extend(
            _expand_entries(
                member_name, f"{part_name}.{member_name}", source, target
            )
        )
        mapped.add(member_name)

    unmapped = [
        name
        for name, member in set_members.items()
        if member.value is not None and name not in mapped
    ]
    if unmapped:
        raise ValueError(
            f"Whole-object bind of '{application.usage_name}' to {part_name} cannot "
            f"map set members {', '.join(sorted(unmapped))}; use per-member binds "
            "for differently named parameters"
        )
    return entries


def mapping_entries(
    architecture: Architecture,
    system: PartDefinition,
    application: AppliedSet,
) -> list[tuple[str, str]]:
    """SSP ``(source, target)`` mapping entries for one applied set."""
    part_def = architecture.resolve_part(application.part_usage)
    if part_def is None:
        raise ValueError(
            f"Unresolved part definition for {application.part_usage.name}"
        )
    interface = parameter_interface(architecture, part_def)
    if interface is None:
        raise ValueError(
            f"{part_def.name} declares no parameter interface, but "
            f"'{application.usage_name}' is bound to {application.part_usage.name}"
        )

    part_name = application.part_usage.name
    if application.identity:
        return _identity_entries(application, interface, part_name)

    set_members = application.set_definition.attributes
    entries: list[tuple[str, str]] = []
    bound_sources: set[str] = set()
    for binding in application.bindings:
        if len(binding.source) != 2 or len(binding.target) != 3:
            raise ValueError(
                "Per-member parameter bindings must have the shape "
                "'<set>.<member> = <component>.parameters.<member>', got "
                f"'{'.'.join(binding.source)} = {'.'.join(binding.target)}'"
            )
        source_name = binding.source[1]
        target_name = binding.target[2]
        source = set_members.get(source_name)
        if source is None:
            raise ValueError(
                f"Parameter set '{application.set_definition.name}' has no member "
                f"'{source_name}'"
            )
        target = interface.attributes.get(target_name)
        if target is None:
            raise ValueError(
                f"Parameter interface '{interface.name}' has no member '{target_name}'"
            )
        _member_type_error(source, target, source_name, target_name)
        entries.extend(
            _expand_entries(
                source_name, f"{part_name}.{target_name}", source, target
            )
        )
        bound_sources.add(source_name)

    unused = sorted(
        name
        for name, member in set_members.items()
        if member.value is not None and name not in bound_sources
    )
    if unused:
        warnings.warn(
            f"Parameter set '{application.set_definition.name}' members "
            f"{', '.join(unused)} are not bound to {part_name}; "
            "SSP will ignore them",
            UserWarning,
            stacklevel=2,
        )
    return entries


def validate_parameter_dialect(
    architecture: Architecture, system: PartDefinition
) -> None:
    """Reject a composition that mixes parameter interfaces and flat attributes."""
    bagged: list[str] = []
    legacy: list[str] = []
    for usage in system.parts.values():
        part_def = architecture.resolve_part(usage)
        if part_def is None:
            continue
        if parameter_bag(architecture, part_def) is not None:
            bagged.append(part_def.name)
        elif any(
            not is_control_attribute(name) for name in part_def.attributes
        ):
            legacy.append(part_def.name)
    has_sets = bool(set_usages(architecture, system))
    if legacy and (bagged or has_sets):
        dialect_parts = bagged or ["parameter set usages"]
        raise ValueError(
            "Composition mixes parameter interfaces/sets "
            f"({', '.join(sorted(dialect_parts))}) with flat parameter attributes "
            f"({', '.join(sorted(legacy))}); use one dialect per composition"
        )


def validate_applied_sets(
    architecture: Architecture, system: PartDefinition
) -> None:
    """Resolve every applied set's mapping, raising on invalid applications."""
    for application in applied_sets(architecture, system):
        mapping_entries(architecture, system, application)


def mapping_specs(
    architecture: Architecture, system: PartDefinition
) -> list[MappingSpec]:
    """Mapping entries for every applied set in a composition."""
    validate_marker_definitions(architecture)
    specs: list[MappingSpec] = []
    for application in applied_sets(architecture, system):
        specs.append(
            MappingSpec(
                set_name=application.set_definition.name,
                set_usage=application.usage_name,
                part_name=application.part_usage.name,
                identity=application.identity,
                entries=tuple(mapping_entries(architecture, system, application)),
            )
        )
    return specs


# -- generation helpers -----------------------------------------------------


def parameter_sets_for_generation(
    architecture: Architecture,
    system: PartDefinition,
    *,
    set_names: list[str] | None = None,
    all_sets: bool = False,
) -> list[AttributeDefinition]:
    """Resolve the set definitions to emit, in deterministic name order."""
    if set_names:
        definitions: list[AttributeDefinition] = []
        for name in set_names:
            definition = architecture.attribute_definitions.get(name)
            if definition is None:
                raise ValueError(f"Unknown parameter set '{name}'")
            if not is_parameter_set(definition):
                raise ValueError(
                    f"'{name}' is not marked ':> {PARAMETER_SET_MARKER}'"
                )
            definitions.append(definition)
        return sorted(definitions, key=lambda item: item.name)

    if all_sets:
        return sorted(
            (
                definition
                for definition in architecture.attribute_definitions.values()
                if is_parameter_set(definition)
            ),
            key=lambda item: item.name,
        )

    definitions = {
        application.set_definition.name: application.set_definition
        for application in applied_sets(architecture, system)
    }
    return sorted(definitions.values(), key=lambda item: item.name)


def uses_parameter_sets(
    architecture_path, composition: str
) -> bool:
    """True when the composition uses the interface/set dialect."""
    architecture = load(architecture_path)
    system = architecture.get_part_def(composition)
    return has_parameter_dialect(architecture, system)
