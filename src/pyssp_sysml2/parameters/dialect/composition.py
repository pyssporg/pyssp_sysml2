"""Composition traversal, parameter binds, and applied parameter sets."""

from __future__ import annotations

from dataclasses import dataclass

from pyssp_sysml2.core.control import is_control_attribute
from pyssp_sysml2.metadata.fmu_metadata import (
    FMU_METADATA_ATTR,
    fmu_metadata,
    is_fmu_metadata_definition,
    validate_retired_control_attributes,
)
from pyssp_sysml2.metadata.roles import is_ssp_model, is_study
from pyssp_sysml2.metadata.ssp_metadata import (
    is_ssp_metadata_definition,
    ssp_metadata,
)
from pyssp_sysml2.model import (
    Architecture,
    Attribute,
    AttributeDefinition,
    Binding,
    PartDefinition,
    PartUsage,
)
from pyssp_sysml2.parameters.dialect.declarations import parameter_port
from pyssp_sysml2.parameters.dialect.markers import (
    PARAMETER_SET_MARKER,
    PARAMETERS_PORT_NAME,
    is_parameter_set,
)


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
        parts = self.port_path + (PARAMETERS_PORT_NAME,)
        if self.port_member is not None:
            parts += (self.port_member,)
        return ".".join(parts)



# -- component traversal and applied sets -------------------------------


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
        index for index, name in enumerate(left) if name == PARAMETERS_PORT_NAME
    ]
    right_indexes = [
        index for index, name in enumerate(right) if name == PARAMETERS_PORT_NAME
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
            f"'{PARAMETERS_PORT_NAME}' segment: '{'.'.join(left)}'"
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
        parameter_port(architecture, ref.part_def) is not None
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
        if is_ssp_model(architecture, ref.part_def):
            # Model-owned bindings belong to the exported model, not the study.
            continue
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



# -- dialect validation ----------------------------------------------------


def _is_metadata_attribute(
    architecture: Architecture, attribute: Attribute
) -> bool:
    definition = architecture.resolve_attribute_def(attribute)
    return is_fmu_metadata_definition(architecture, definition)


def _is_ssp_metadata_attribute(
    architecture: Architecture, attribute: Attribute
) -> bool:
    definition = architecture.resolve_attribute_def(attribute)
    return is_ssp_metadata_definition(architecture, definition)


def _reject_flat_attributes(
    architecture: Architecture, part_def: PartDefinition
) -> None:
    for name, attribute in part_def.attributes.items():
        if is_control_attribute(name):
            continue
        if _is_metadata_attribute(architecture, attribute):
            if part_def.parts:
                raise ValueError(
                    f"{part_def.name}.{name} is FMU metadata, but the part has "
                    "subparts; a nested system cannot also be an FMU component"
                )
            fmu_metadata(architecture, part_def)
            continue
        if _is_ssp_metadata_attribute(architecture, attribute):
            ssp_metadata(architecture, part_def)
            continue
        definition = architecture.resolve_attribute_def(attribute)
        if is_parameter_set(definition):
            # A model-owned scenario set usage; applied sets are validated by
            # mapping_specs and the exporting generator.
            continue
        if name == FMU_METADATA_ATTR:
            raise ValueError(
                f"{part_def.name}.{name} must be typed by an attribute def "
                "marked ':> FmuMetadata'"
            )
        raise ValueError(
            f"{part_def.name}.{name} is a flat parameter attribute, which is no "
            "longer supported. Declare a parameter interface with "
            f"'in port {PARAMETERS_PORT_NAME} : <Interface>;' and apply a "
            "ParameterSet with 'bind'."
        )


def validate_parameter_dialect(
    architecture: Architecture, system: PartDefinition
) -> None:
    """Reject retired flat parameters and unsupported model attributes.

    Parameters must come from a parameter interface. The composition may carry
    control attributes and parameter-set usages, but no flat parameters.
    """
    validate_retired_control_attributes(architecture)

    for part_def in component_definitions(architecture, system):
        _reject_flat_attributes(architecture, part_def)

    for name, attribute in system.attributes.items():
        if is_control_attribute(name):
            continue
        if _is_metadata_attribute(architecture, attribute):
            raise ValueError(
                f"{system.name}.{name} is FMU metadata, but the composition is "
                "not an FMU component"
            )
        if _is_ssp_metadata_attribute(architecture, attribute) and is_study(
            architecture, system
        ):
            raise ValueError(
                f"{system.name}.{name} is SSP metadata; declare it on the "
                "SspModel composition"
            )
        definition = architecture.resolve_attribute_def(attribute)
        if definition is not None:
            # Set usages (and other value attributes) are resolved by the
            # parameter/bind validation, which reports role errors precisely.
            continue
        raise ValueError(
            f"{system.name}.{name} is a flat parameter attribute, which is no "
            "longer supported. Define parameter sets inside SysML and bind them "
            "to component usages."
        )
