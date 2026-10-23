"""Typed FMU metadata carried by part definitions.

The dialect is a small value-definition hierarchy::

    attribute def FmuMetadata {
      attribute source : String;
      attribute implementation : String;
    }

    attribute def AutopilotFmu :> FmuMetadata {
      attribute source = "build/fmus/Autopilot.fmu";
      attribute implementation = "CoSimulation";
    }

    part def AutopilotModule {
      attribute fmu_meta : AutopilotFmu;
    }

Metadata is recognized by **type**, not by the usage name: the part attribute
must be typed by an ``attribute def`` that specializes ``FmuMetadata``. At most
one such attribute is allowed per part definition.

``source`` is the build artifact path (a ``.fmu`` file or an extracted FMU
directory). It is authoring data and is never recovered from an SSD. A part
definition without ``source`` has no FMU yet: its SSD component is exported
with an empty ``source``. ``implementation`` maps to
``ssd:Component/@implementation``; the FMU resource name is always derived
from the part definition name.
"""

from __future__ import annotations

from dataclasses import dataclass

from pyssp_sysml2.control import RETIRED_CONTROL_ATTRS
from pyssp_sysml2.fmi_helpers import fmu_resource_path
from pyssp_sysml2.sysml_model import (
    Architecture,
    Attribute,
    AttributeDefinition,
    PartDefinition,
)

FMU_METADATA_ATTR = "fmu_meta"
FMU_METADATA_MARKER = "FmuMetadata"
FMU_METADATA_FIELDS = ("source", "implementation")


@dataclass(frozen=True)
class FmuMetadata:
    """Effective metadata values for one FMU-backed part definition."""

    source: str | None = None
    implementation: str | None = None


# -- definition resolution --------------------------------------------------


def _short_name(name: str) -> str:
    return name.split("::")[-1]


def _attribute_def(
    architecture: Architecture, name: str | None
) -> AttributeDefinition | None:
    if not name:
        return None
    return architecture.attribute_definitions.get(_short_name(name))


def is_fmu_metadata_definition(
    architecture: Architecture, definition: AttributeDefinition | None
) -> bool:
    """True when ``definition`` is the marker or specializes it transitively."""
    return _specializes_marker(architecture, definition, FMU_METADATA_MARKER)


def _specializes_marker(
    architecture: Architecture,
    definition: AttributeDefinition | None,
    marker: str,
    seen: set[str] | None = None,
) -> bool:
    if definition is None:
        return False
    if _short_name(definition.name) == marker:
        return True
    seen = set() if seen is None else seen
    if definition.name in seen:
        return False
    seen.add(definition.name)
    for supertype in definition.specializes:
        if _short_name(supertype) == marker:
            return True
        base = _attribute_def(architecture, supertype)
        if _specializes_marker(architecture, base, marker, seen):
            return True
    return False


def _effective_members(
    architecture: Architecture,
    definition: AttributeDefinition,
    seen: set[str] | None = None,
) -> dict[str, Attribute]:
    """Direct members plus inherited members; derived values win by name."""
    seen = set() if seen is None else seen
    if definition.name in seen:
        return {}
    seen.add(definition.name)

    members: dict[str, Attribute] = {}
    for supertype in definition.specializes:
        base = _attribute_def(architecture, supertype)
        if base is not None:
            members.update(_effective_members(architecture, base, seen))
    for name, attribute in definition.attributes.items():
        inherited = members.get(name)
        if (
            attribute.value is None
            and inherited is not None
            and inherited.value is not None
        ):
            members[name] = inherited
        else:
            members[name] = attribute
    return members


def _metadata_usage(
    architecture: Architecture, part_def: PartDefinition
) -> tuple[str, Attribute, AttributeDefinition] | None:
    found: list[tuple[str, Attribute, AttributeDefinition]] = []
    for name, attribute in part_def.attributes.items():
        definition = architecture.resolve_attribute_def(attribute)
        if is_fmu_metadata_definition(architecture, definition):
            assert definition is not None
            found.append((name, attribute, definition))

    if len(found) > 1:
        names = ", ".join(sorted(name for name, _, _ in found))
        raise ValueError(
            f"{part_def.name} declares multiple FMU metadata attributes "
            f"({names}); use one"
        )
    if found:
        name, attribute, definition = found[0]
        if _short_name(definition.name) == FMU_METADATA_MARKER:
            raise ValueError(
                f"{part_def.name}.{name} is typed by the '{FMU_METADATA_MARKER}' "
                "schema directly; use a concrete 'attribute def <Part>FmuMetadata "
                f":> {FMU_METADATA_MARKER} {{ ... }}' instead"
            )
        return name, attribute, definition

    if FMU_METADATA_ATTR in part_def.attributes:
        raise ValueError(
            f"{part_def.name}.{FMU_METADATA_ATTR} must be typed by an "
            f"attribute def marked ':> {FMU_METADATA_MARKER}'"
        )
    return None


def _string_member(name: str, attribute: Attribute | None) -> str | None:
    if attribute is None or attribute.value is None:
        return None
    value = attribute.value
    if not isinstance(value, str) or attribute.primitive_type_str() != "String":
        actual = attribute.primitive_type_str()
        raise ValueError(
            f"Fmu metadata member '{name}' must be a String, got {actual}"
        )
    return value


def fmu_metadata(
    architecture: Architecture, part_def: PartDefinition
) -> FmuMetadata | None:
    """Resolve effective FMU metadata for ``part_def``, or ``None``."""
    usage = _metadata_usage(architecture, part_def)
    if usage is None:
        return None

    name, _attribute, definition = usage
    if part_def.parts:
        raise ValueError(
            f"{part_def.name} has both subparts and '{name}' metadata; "
            "a nested system cannot also be an FMU component"
        )

    marker = architecture.attribute_definitions.get(FMU_METADATA_MARKER)
    if marker is None:
        raise ValueError(
            f"FMU metadata uses missing marker definition '{FMU_METADATA_MARKER}'. "
            f"Add 'attribute def {FMU_METADATA_MARKER} {{ ... }}' to the package."
        )

    members = _effective_members(architecture, definition)
    unknown = sorted(set(members) - set(FMU_METADATA_FIELDS))
    if unknown:
        raise ValueError(
            f"FMU metadata definition '{definition.name}' declares unsupported "
            f"member(s): {', '.join(unknown)}; allowed members are "
            f"{', '.join(FMU_METADATA_FIELDS)}"
        )

    return FmuMetadata(
        source=_string_member("source", members.get("source")),
        implementation=_string_member(
            "implementation", members.get("implementation")
        ),
    )


def component_source(part_def: PartDefinition, metadata: FmuMetadata | None) -> str:
    """SSD component source; empty when no FMU is authored for the part."""
    if metadata is None or not metadata.source:
        return ""
    return fmu_resource_path(part_def.name)


def component_implementation(metadata: FmuMetadata | None) -> str | None:
    return None if metadata is None else metadata.implementation


# -- synthesis --------------------------------------------------------------


def ensure_fmu_metadata_definition(
    architecture: Architecture, source_file: str
) -> AttributeDefinition:
    """Create the shared ``FmuMetadata`` schema when it is missing."""
    existing = architecture.attribute_definitions.get(FMU_METADATA_MARKER)
    if existing is not None:
        return existing
    if FMU_METADATA_MARKER in architecture.port_definitions:
        raise ValueError(
            f"'{FMU_METADATA_MARKER}' is defined as a port def, but FMU metadata "
            "is an attribute def"
        )

    definition = AttributeDefinition(
        name=FMU_METADATA_MARKER,
        source_file=source_file,
    )
    for field in FMU_METADATA_FIELDS:
        definition.attributes[field] = Attribute(name=field, type_name="String")
    architecture.add_attribute_def(definition)
    return definition


def _unique_definition_name(architecture: Architecture, base: str) -> str:
    candidate = base
    counter = 2
    used = set(architecture.attribute_definitions) | set(architecture.port_definitions)
    while candidate in used:
        candidate = f"{base}_{counter}"
        counter += 1
    return candidate


def _metadata_definition_name(part_def: PartDefinition) -> str:
    return f"{part_def.name}FmuMetadata"


def add_fmu_metadata(
    architecture: Architecture,
    part_def: PartDefinition,
    *,
    implementation: str | None = None,
    source_file: str,
) -> AttributeDefinition:
    """Attach a concrete metadata definition and ``fmu_meta`` usage."""
    ensure_fmu_metadata_definition(architecture, source_file)
    if FMU_METADATA_ATTR in part_def.attributes:
        raise ValueError(
            f"{part_def.name}.{FMU_METADATA_ATTR} already exists; update it "
            "instead of adding a second metadata attribute"
        )

    name = _unique_definition_name(
        architecture, _metadata_definition_name(part_def)
    )
    definition = AttributeDefinition(
        name=name,
        source_file=source_file,
        specializes=(FMU_METADATA_MARKER,),
    )
    if implementation is not None:
        definition.attributes["implementation"] = Attribute(
            name="implementation", type_name="String", value=implementation
        )

    architecture.add_attribute_def(definition)
    part_def.attributes[FMU_METADATA_ATTR] = Attribute(
        name=FMU_METADATA_ATTR,
        type_name=name,
    )
    return definition


def _definition_is_shared(
    architecture: Architecture,
    definition: AttributeDefinition,
    owner: PartDefinition,
) -> bool:
    for part_def in architecture.part_definitions.values():
        if part_def is owner:
            continue
        for usage in part_def.attributes.values():
            if architecture.resolve_attribute_def(usage) is definition:
                return True
    return False


def _clone_metadata_definition(
    architecture: Architecture,
    definition: AttributeDefinition,
    part_def: PartDefinition,
    usage_name: str,
    source_file: str,
) -> AttributeDefinition:
    name = _unique_definition_name(
        architecture, _metadata_definition_name(part_def)
    )
    clone = AttributeDefinition(
        name=name,
        doc=definition.doc,
        source_file=source_file,
        specializes=definition.specializes,
    )
    for field, attribute in definition.attributes.items():
        clone.attributes[field] = Attribute(
            name=attribute.name,
            type_name=attribute.type_name,
            value=attribute.value,
            doc=attribute.doc,
            multiplicity=attribute.multiplicity,
        )
    architecture.add_attribute_def(clone)
    part_def.attributes[usage_name] = Attribute(
        name=usage_name,
        type_name=name,
    )
    return clone


def update_fmu_metadata_from_component(
    architecture: Architecture,
    part_def: PartDefinition,
    component,
    *,
    source_file: str,
) -> None:
    """Reconcile ``implementation`` with an SSD component.

    ``source`` is authoring data and is preserved. No metadata is created when
    the component carries no implementation.
    """
    implementation = getattr(component, "implementation", None)

    usage = _metadata_usage(architecture, part_def)
    if usage is None:
        if implementation:
            add_fmu_metadata(
                architecture,
                part_def,
                implementation=implementation,
                source_file=source_file,
            )
        return

    usage_name, _attribute, definition = usage
    if _definition_is_shared(architecture, definition, part_def):
        definition = _clone_metadata_definition(
            architecture, definition, part_def, usage_name, source_file
        )

    if implementation:
        definition.attributes["implementation"] = Attribute(
            name="implementation",
            type_name="String",
            value=implementation,
        )
    else:
        definition.attributes.pop("implementation", None)

    if not definition.attributes:
        part_def.attributes.pop(usage_name, None)
        architecture.attribute_definitions.pop(definition.name, None)


def validate_retired_control_attributes(architecture: Architecture) -> None:
    """Reject attributes removed by the typed-metadata migration."""
    definitions = list(architecture.part_definitions.values()) + list(
        architecture.port_definitions.values()
    )
    for definition in definitions:
        for name in definition.attributes:
            message = RETIRED_CONTROL_ATTRS.get(name)
            if message is not None:
                raise ValueError(
                    f"{definition.name}.{name} is no longer supported; {message}"
                )
