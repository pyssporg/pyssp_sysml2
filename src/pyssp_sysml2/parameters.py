"""Parameter interfaces, parameter sets, and SSP mapping helpers.

The dialect this module implements:

- a **parameter interface** is an ``attribute def`` marked ``:>
  ParameterInterface``;
- a parameter **set** is an ``attribute def`` marked ``:> ParameterSet``;
- a component or nested system exposes an interface through a single
  fixed-name bag, ``attribute parameters : <Interface>;``;
- a composition applies one or more sets per component usage with ``bind``:
  either a whole-object bind (identity mapping) or one bind per member
  (explicit mapping);
- multiple sets on one component must bind disjoint target members, because
  SysML ``bind`` is equality, not an override.

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


# -- component paths and applied sets ---------------------------------------


@dataclass(frozen=True)
class ComponentRef:
    """A part usage reached from a composition root."""

    path: tuple[str, ...]
    part_usage: PartUsage
    part_def: PartDefinition

    @property
    def name(self) -> str:
        return ".".join(self.path)


@dataclass(frozen=True)
class AppliedSet:
    """One composition usage applying a set to one component usage."""

    usage_name: str
    set_definition: AttributeDefinition
    component_path: tuple[str, ...]
    part_usage: PartUsage
    bindings: tuple[ParameterBind, ...]
    identity: bool

    @property
    def component_name(self) -> str:
        return ".".join(self.component_path)


@dataclass(frozen=True)
class MappingSpec:
    """Mapping entries for one (set, component usage) application."""

    set_name: str
    set_usage: str
    component_path: tuple[str, ...]
    identity: bool
    entries: tuple[tuple[str, str], ...]

    @property
    def component_name(self) -> str:
        return ".".join(self.component_path)


@dataclass(frozen=True)
class ParameterBind:
    """A parameter bind resolved by role, not by written position.

    Canonical form puts the parameter port on the left and the set usage on
    the right::

        bind <component-path>.parameters[.<member>] = <set>[.<member>];

    ``bind`` is equality in SysML, so the endpoints are identified by the
    ``parameters`` segment. Only that canonical orientation is accepted; the
    reversed form is rejected with the rewritten bind in the error message.
    """

    binding: Binding
    port_path: tuple[str, ...]
    port_member: str | None
    set_path: tuple[str, ...]

    @property
    def set_usage(self) -> str:
        return self.set_path[0]

    @property
    def set_member(self) -> str | None:
        return self.set_path[1] if len(self.set_path) == 2 else None

    @property
    def identity(self) -> bool:
        """True for a whole-object bind (``<port> = <set>``)."""
        return self.port_member is None

    def port_reference(self) -> str:
        """The left-hand feature chain, for error messages."""
        parts = self.port_path + (PARAMETERS_BAG_NAME,)
        if self.port_member is not None:
            parts += (self.port_member,)
        return ".".join(parts)


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


def component_refs(
    architecture: Architecture, system: PartDefinition
) -> list[ComponentRef]:
    """Every part usage below ``system``, including nested system usages."""
    refs: list[ComponentRef] = []

    def walk(
        part_def: PartDefinition,
        prefix: tuple[str, ...],
        ancestors: frozenset[str],
    ) -> None:
        for usage in part_def.parts.values():
            path = prefix + (usage.name,)
            child = architecture.resolve_part(usage)
            if child is None:
                raise ValueError(
                    f"Unresolved part definition for {'.'.join(path)}"
                )
            refs.append(
                ComponentRef(path=path, part_usage=usage, part_def=child)
            )
            if child.parts:
                if child.name in ancestors:
                    raise ValueError(
                        "Recursive part hierarchy at "
                        f"'{'.'.join(path)}' ({child.name})"
                    )
                walk(child, path, ancestors | {child.name})

    walk(system, (), frozenset({system.name}))
    return refs


def component_definitions(
    architecture: Architecture, system: PartDefinition
) -> list[PartDefinition]:
    """Unique part definitions reachable from ``system``, in path order."""
    definitions: list[PartDefinition] = []
    seen: set[str] = set()
    for ref in component_refs(architecture, system):
        if ref.part_def.name in seen:
            continue
        seen.add(ref.part_def.name)
        definitions.append(ref.part_def)
    return definitions


def parameter_bind(binding: Binding) -> ParameterBind | None:
    """Resolve a bind by role, or ``None`` for a non-parameter bind.

    Only the canonical orientation is accepted: the parameter port must be
    on the left of ``=``. The ``parameters`` segment must appear exactly once
    on that side and be followed by at most one member name.
    """
    left = list(binding.source)
    right = list(binding.target)
    left_indexes = [
        index for index, name in enumerate(left) if name == PARAMETERS_BAG_NAME
    ]
    right_indexes = [
        index for index, name in enumerate(right) if name == PARAMETERS_BAG_NAME
    ]

    if not left_indexes and not right_indexes:
        return None
    if left_indexes and right_indexes:
        raise ValueError(
            f"Parameter bind '{binding.key}' connects two parameter ports; "
            "bind a parameter port to a parameter set, or use a connection"
        )
    if right_indexes:
        raise ValueError(
            f"Parameter bind '{binding.key}' must be written with the "
            "parameter port on the left:\n"
            f"  bind {'.'.join(right)} = {'.'.join(left)};"
        )
    if len(left_indexes) > 1:
        raise ValueError(
            "Parameter bind target contains more than one "
            f"'{PARAMETERS_BAG_NAME}' segment: '{'.'.join(left)}'"
        )

    index = left_indexes[0]
    port_path = tuple(left[:index])
    rest = left[index + 1 :]
    if len(rest) > 1:
        raise ValueError(
            "Parameter bind targets must be '<component>.parameters' or "
            f"'<component>.parameters.<member>', got '{'.'.join(left)}'"
        )
    port_member = rest[0] if rest else None

    set_path = tuple(right)
    if len(set_path) not in (1, 2):
        raise ValueError(
            "Parameter bind sources must be '<set>' or '<set>.<member>', "
            f"got '{'.'.join(right)}'"
        )
    if (port_member is None) != (len(set_path) == 1):
        raise ValueError(
            "Parameter binds must bind a whole set to '<component>.parameters' "
            "or one set member to '<component>.parameters.<member>', got "
            f"'{binding.key}'"
        )

    return ParameterBind(
        binding=binding,
        port_path=port_path,
        port_member=port_member,
        set_path=set_path,
    )


def has_parameter_dialect(
    architecture: Architecture, system: PartDefinition
) -> bool:
    """True when a composition uses parameter interfaces/sets or bindings."""
    if set_usages(architecture, system):
        return True
    if any(
        parameter_bind(binding) is not None
        for binding in system.bindings
    ):
        return True
    return any(
        parameter_bag(architecture, ref.part_def) is not None
        for ref in component_refs(architecture, system)
    )


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


def _resolve_set_definition(
    architecture: Architecture,
    system: PartDefinition,
    usage_name: str,
    component_name: str,
) -> AttributeDefinition:
    usage = system.attributes.get(usage_name)
    if usage is None:
        raise ValueError(
            f"Binding for {component_name} references '{usage_name}', "
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
    return definition


def _applied_sets_for_component(
    architecture: Architecture,
    system: PartDefinition,
    ref: ComponentRef,
) -> list[AppliedSet]:
    grouped: dict[str, list[ParameterBind]] = {}
    for binding in system.bindings:
        bind = parameter_bind(binding)
        if bind is None or bind.port_path != ref.path:
            continue
        grouped.setdefault(bind.set_usage, []).append(bind)

    applications: list[AppliedSet] = []
    for usage_name, binds in sorted(grouped.items()):
        kinds = {
            "identity" if bind.identity else "member"
            for bind in binds
        }
        if len(kinds) > 1:
            raise ValueError(
                f"{ref.name} mixes whole-object and per-member parameter binds "
                f"for set '{usage_name}'; use one form per set"
            )
        applications.append(
            AppliedSet(
                usage_name=usage_name,
                set_definition=_resolve_set_definition(
                    architecture, system, usage_name, ref.name
                ),
                component_path=ref.path,
                part_usage=ref.part_usage,
                bindings=tuple(binds),
                identity=("identity" in kinds),
            )
        )
    return applications


def applied_sets(
    architecture: Architecture, system: PartDefinition
) -> list[AppliedSet]:
    """Every set applied to every component usage below ``system``.

    Multiple sets may apply to one component. They must bind disjoint target
    members; overlap is rejected by :func:`validate_applied_sets`.
    """
    refs = component_refs(architecture, system)
    refs_by_path = {ref.path: ref for ref in refs}

    for binding in system.bindings:
        bind = parameter_bind(binding)
        if bind is None:
            continue
        if bind.port_path not in refs_by_path:
            raise ValueError(
                "Parameter bind target "
                f"'{bind.port_reference()}' does not resolve to a component "
                "usage"
            )

    seen_definitions: set[str] = set()
    for ref in refs:
        if ref.part_def.name in seen_definitions:
            continue
        seen_definitions.add(ref.part_def.name)
        if any(
            parameter_bind(binding) is not None
            for binding in ref.part_def.bindings
        ):
            raise ValueError(
                f"Parameter binds inside nested part definition "
                f"'{ref.part_def.name}' are not supported; apply sets at the "
                "composition root"
            )

    applications: list[AppliedSet] = []
    for ref in refs:
        applications.extend(
            _applied_sets_for_component(architecture, system, ref)
        )
    return applications


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
    application: AppliedSet,
    interface: AttributeDefinition,
    component_name: str,
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
            source, target, member_name, f"{component_name}.{member_name}"
        )
        entries.extend(
            _expand_entries(
                member_name,
                f"{component_name}.{member_name}",
                source,
                target,
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
            f"Whole-object bind of '{application.usage_name}' to {component_name} "
            f"cannot map set members {', '.join(sorted(unmapped))}; use "
            "per-member binds for differently named parameters"
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
            f"Unresolved part definition for {application.component_name}"
        )
    interface = parameter_interface(architecture, part_def)
    if interface is None:
        raise ValueError(
            f"{part_def.name} declares no parameter interface, but "
            f"'{application.usage_name}' is bound to {application.component_name}"
        )

    component_name = application.component_name
    if application.identity:
        return _identity_entries(application, interface, component_name)

    set_members = application.set_definition.attributes
    entries: list[tuple[str, str]] = []
    bound_sources: set[str] = set()
    for bind in application.bindings:
        if (
            bind.port_path != application.component_path
            or bind.port_member is None
            or bind.set_member is None
        ):
            raise ValueError(
                "Per-member parameter binds must have the shape "
                "'<component>.parameters.<member> = <set>.<member>', got "
                f"'{'.'.join(bind.binding.source)} = "
                f"{'.'.join(bind.binding.target)}'"
            )
        source_name = bind.set_member
        target_name = bind.port_member
        source = set_members.get(source_name)
        if source is None:
            raise ValueError(
                f"Parameter set '{application.set_definition.name}' has no member "
                f"'{source_name}'"
            )
        target_attribute = interface.attributes.get(target_name)
        if target_attribute is None:
            raise ValueError(
                f"Parameter interface '{interface.name}' has no member '{target_name}'"
            )
        _member_type_error(source, target_attribute, source_name, target_name)
        entries.extend(
            _expand_entries(
                source_name,
                f"{component_name}.{target_name}",
                source,
                target_attribute,
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
            f"{', '.join(unused)} are not bound to {component_name}; "
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
    for part_def in component_definitions(architecture, system):
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


def _validate_disjoint_targets(
    applications: list[tuple[AppliedSet, tuple[tuple[str, str], ...]]],
) -> None:
    """Reject two sets that bind the same component member.

    Multiple sets on one component are allowed only when their target members
    are disjoint. SysML ``bind`` has equality semantics, not an override order,
    so overlapping targets would be ambiguous when mapped to SSP.
    """
    by_component: dict[str, list[tuple[str, set[str]]]] = {}
    for application, entries in applications:
        component_name = application.component_name
        prefix = component_name + "."
        members: set[str] = set()
        for _source_name, target_name in entries:
            if not target_name.startswith(prefix):
                raise ValueError(
                    f"Parameter target '{target_name}' is outside component "
                    f"'{component_name}'"
                )
            members.add(target_name[len(prefix) :].split("[", 1)[0])
        by_component.setdefault(component_name, []).append(
            (application.usage_name, members)
        )

    for component_name, component_applications in by_component.items():
        seen: dict[str, str] = {}
        for usage_name, members in component_applications:
            for member_name in members:
                previous = seen.get(member_name)
                if previous is not None:
                    if previous == usage_name:
                        continue
                    raise ValueError(
                        f"Multiple parameter sets bind "
                        f"'{component_name}.{member_name}': {previous}, "
                        f"{usage_name}. Use disjoint target members."
                    )
                seen[member_name] = usage_name


def validate_applied_sets(
    architecture: Architecture, system: PartDefinition
) -> None:
    """Resolve every applied set's mapping and reject overlapping targets."""
    mapping_specs(architecture, system)


def mapping_specs(
    architecture: Architecture, system: PartDefinition
) -> list[MappingSpec]:
    """Mapping entries for every applied set in a composition."""
    validate_marker_definitions(architecture)
    applications = [
        (
            application,
            tuple(mapping_entries(architecture, system, application)),
        )
        for application in applied_sets(architecture, system)
    ]
    _validate_disjoint_targets(applications)
    specs = [
        MappingSpec(
            set_name=application.set_definition.name,
            set_usage=application.usage_name,
            component_path=application.component_path,
            identity=application.identity,
            entries=entries,
        )
        for application, entries in applications
    ]
    return sorted(
        specs, key=lambda spec: (spec.component_path, spec.set_name)
    )


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
