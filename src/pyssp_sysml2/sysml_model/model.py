"""Stable in-memory SysML v2 architecture model for pyssp_sysml2.

This module is the repo-owned contract between the sysmlpy-backed loader
(`pyssp_sysml2.sysml_model.loader`) and every generator
(`ssd.py`, `ssv.py`, `fmi.py`, `sysml.py`, `sync.py`).

Design rule: nothing outside `loader.py` may import `sysmlpy`. All repo code
works against the dataclasses below, so a sysmlpy API change can only break
the loader, and a future parser swap only touches the loader.

Value semantics (mirrors the retired `pycps_sysmlv2` contract):

- ``Attribute.value`` is Python-native: ``None``, ``bool``, ``int``, ``float``,
  ``str``, or a ``tuple`` for list-valued attributes.
- Attribute types are plain names (``"Real"``, ``"Integer"``, ``"Boolean"``,
  ``"String"``, or a custom name). Unknown/custom types degrade to ``Real``
  where a primitive is required, matching the generators' fallback behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

__all__ = [
    "Architecture",
    "Attribute",
    "AttributeDefinition",
    "Binding",
    "Connection",
    "Definition",
    "PartDefinition",
    "PartUsage",
    "PortDefinition",
    "PortUsage",
    "RequirementDefinition",
    "endpoint_text",
]

# Lowercase alias map for the primitive types the generators understand.
# Mirrors the retired SYSML_TYPE_MAP so degraded lookups behave the same.
_TYPE_ALIASES = {
    "real": "Real",
    "float": "Real",
    "float32": "Real",
    "float64": "Real",
    "double": "Real",
    "integer": "Integer",
    "int": "Integer",
    "int8": "Integer",
    "int32": "Integer",
    "uint8": "Integer",
    "uint32": "Integer",
    "boolean": "Boolean",
    "bool": "Boolean",
    "string": "String",
}


def _primitive_from_value(value) -> str | None:
    """Infer a primitive type name from a Python literal value."""
    if isinstance(value, bool):
        return "Boolean"
    if isinstance(value, int):
        return "Integer"
    if isinstance(value, float):
        return "Real"
    if isinstance(value, str):
        return "String"
    return None


@dataclass
class Attribute:
    """A valued or typed attribute on a part/port definition.

    ``multiplicity`` is the declared range as written (``"3"``, ``"0..*"``,
    ``"2..4"``) or ``None`` when the attribute is scalar/undeclared.
    """

    name: str
    type_name: str | None = None
    value: object = None
    doc: str | None = None
    multiplicity: str | None = None

    @property
    def is_list(self) -> bool:
        return isinstance(self.value, tuple)

    @property
    def effective_type_name(self) -> str | None:
        """Declared type name, or the type inferred from the value."""
        if self.type_name:
            return self.type_name
        value = self.value
        if isinstance(value, tuple) and value:
            value = value[0]
        return _primitive_from_value(value)

    def primitive_type_str(self) -> str:
        """Real/Integer/Boolean/String for this attribute's element type.

        List-valued attributes report the element primitive. Unknown/custom
        types fall back to the value's primitive, then to ``Real`` — the same
        degradation the FMI/SSV generators apply to unknown types.
        """
        name = self.effective_type_name
        if name is not None:
            primitive = _TYPE_ALIASES.get(name.strip().lower())
            if primitive is not None:
                return primitive
        value = self.value
        if isinstance(value, tuple) and value:
            value = value[0]
        return _primitive_from_value(value) or "Real"

    def enumerator(self, start: int = 0) -> enumerate:
        """Zero-based ``(index, value)`` enumeration; scalars are wrapped."""
        value = self.value
        if not isinstance(value, tuple):
            value = (value,)
        return enumerate(value, start=start)


@dataclass
class PortUsage:
    """A port usage inside a part definition (``in port sig : Signal;``)."""

    name: str
    direction: str | None  # "in" | "out" | "inout" | None (undirected)
    type_name: str
    doc: str | None = None


@dataclass
class PartUsage:
    """A typed part usage inside a composition (``part src : Source;``)."""

    name: str
    type_name: str
    doc: str | None = None


def endpoint_text(part: str | None, port: str) -> str:
    """Text form of one connection endpoint.

    A ``None`` part is a port of the enclosing part def, i.e. the system
    boundary, written without a qualifier.
    """
    return port if part is None else f"{part}.{port}"


@dataclass
class Connection:
    """A ``connect source.port to destination.port;`` inside a part def.

    An endpoint without a part (``connect gain.y to y;`` or
    ``connect u to gain.u;``) refers to a port of the enclosing part def: the
    connection crosses the system boundary. The SSD omits
    ``startElement``/``endElement`` for such an endpoint.
    """

    name: str
    source_part: str | None
    source_port: str
    destination_part: str | None
    destination_port: str
    doc: str | None = None

    @property
    def key(self) -> str:
        return (
            f"{endpoint_text(self.source_part, self.source_port)}"
            f"->{endpoint_text(self.destination_part, self.destination_port)}"
        )


@dataclass
class Binding:
    """A ``bind source.feature = target.feature;`` inside a part def.

    Endpoints are stored as feature-name chains **as written**: ``source`` is
    the left-hand side, ``target`` the right-hand side. SysML ``bind`` is
    equality, but the parameter dialect fixes the orientation, putting the
    parameter port on the left and the set usage on the right::

        bind autopilot.parameters.waypointCount = nominal.waypointCount;

    :func:`pyssp_sysml2.parameters.parameter_bind` resolves the endpoints by
    role and rejects the reversed form.
    """

    source: tuple[str, ...]
    target: tuple[str, ...]
    name: str | None = None

    @property
    def key(self) -> str:
        return f"{'.'.join(self.source)}={'.'.join(self.target)}"


@dataclass
class Definition:
    """Common base for top-level package definitions."""

    name: str
    doc: str | None = None
    source_file: str | None = None


@dataclass
class PortDefinition(Definition):
    """A ``port def`` with ordered attributes and optional supertypes."""

    attributes: dict[str, Attribute] = field(default_factory=dict)
    specializes: tuple[str, ...] = ()


@dataclass
class AttributeDefinition(Definition):
    """An ``attribute def`` with ordered members and optional supertypes.

    Parameter interfaces and parameter sets are both ``attribute def``s;
    their role is established by specialization (``:> ParameterInterface`` /
    ``:> ParameterSet``) and by how they are used.
    """

    attributes: dict[str, Attribute] = field(default_factory=dict)
    specializes: tuple[str, ...] = ()


@dataclass
class PartDefinition(Definition):
    """A ``part def`` with attributes, ports, subparts, and connections."""

    attributes: dict[str, Attribute] = field(default_factory=dict)
    ports: dict[str, PortUsage] = field(default_factory=dict)
    parts: dict[str, PartUsage] = field(default_factory=dict)
    connections: dict[str, Connection] = field(default_factory=dict)
    bindings: list[Binding] = field(default_factory=list)
    specializes: tuple[str, ...] = ()


@dataclass
class RequirementDefinition(Definition):
    """A ``requirement def`` whose doc comment is its text."""

    text: str | None = None


@dataclass
class Architecture:
    """A merged, same-package SysML v2 architecture.

    Member dicts are insertion-ordered; ``connections`` is keyed by
    ``Connection.key`` (``"src.src_port->dst.dst_port"``).
    """

    package_name: str
    part_definitions: dict[str, PartDefinition] = field(default_factory=dict)
    port_definitions: dict[str, PortDefinition] = field(default_factory=dict)
    attribute_definitions: dict[str, AttributeDefinition] = field(default_factory=dict)
    requirement_definitions: dict[str, RequirementDefinition] = field(
        default_factory=dict
    )

    # -- lookups -----------------------------------------------------------

    def get_part_def(self, name: str) -> PartDefinition:
        try:
            return self.part_definitions[name]
        except KeyError:
            raise KeyError(f"Definition not found in namespace: Key:{name}") from None

    def get_port_def(self, name: str) -> PortDefinition:
        try:
            return self.port_definitions[name]
        except KeyError:
            raise KeyError(f"Definition not found in namespace: Key:{name}") from None

    def get_attribute_def(self, name: str) -> AttributeDefinition:
        try:
            return self.attribute_definitions[name]
        except KeyError:
            raise KeyError(f"Definition not found in namespace: Key:{name}") from None

    # -- construction ------------------------------------------------------

    def add_part_def(self, part_def: PartDefinition) -> PartDefinition:
        if part_def.name in self.part_definitions:
            raise ValueError(f"Duplicate part definition for {part_def.name}")
        self.part_definitions[part_def.name] = part_def
        return part_def

    def add_port_def(self, port_def: PortDefinition) -> PortDefinition:
        if port_def.name in self.port_definitions:
            raise ValueError(f"Duplicate port definition for {port_def.name}")
        self.port_definitions[port_def.name] = port_def
        return port_def

    def add_attribute_def(
        self, attribute_def: AttributeDefinition
    ) -> AttributeDefinition:
        if attribute_def.name in self.attribute_definitions:
            raise ValueError(
                f"Duplicate attribute definition for {attribute_def.name}"
            )
        self.attribute_definitions[attribute_def.name] = attribute_def
        return attribute_def

    def add_requirement_def(
        self, requirement_def: RequirementDefinition
    ) -> RequirementDefinition:
        if requirement_def.name in self.requirement_definitions:
            raise ValueError(
                f"Duplicate requirement definition for {requirement_def.name}"
            )
        self.requirement_definitions[requirement_def.name] = requirement_def
        return requirement_def

    # -- usage resolution ----------------------------------------------------

    def resolve_part(self, usage: PartUsage | str) -> PartDefinition | None:
        """The part definition a part usage refers to, or None if unknown."""
        name = usage.type_name if isinstance(usage, PartUsage) else usage
        return self.part_definitions.get(name)

    def resolve_port(self, usage: PortUsage | str) -> PortDefinition | None:
        """The port definition a port usage refers to, or None if unknown."""
        name = usage.type_name if isinstance(usage, PortUsage) else usage
        return self.port_definitions.get(name)

    def resolve_attribute_def(
        self, usage: Attribute | str | None
    ) -> AttributeDefinition | None:
        """The attribute def an attribute usage refers to, or None if unknown."""
        if usage is None:
            return None
        name = usage.type_name if isinstance(usage, Attribute) else usage
        if not name:
            return None
        return self.attribute_definitions.get(name)

    def iter_part_usages(self, part_def: PartDefinition) -> Iterator[PartUsage]:
        return iter(part_def.parts.values())

    # -- export --------------------------------------------------------------

    def export_declared(self) -> dict[str, str]:
        """Per-source-file SysML v2 text; see ``exporter.py`` for the format."""
        from pyssp_sysml2.sysml_model.exporter import export_declared

        return export_declared(self)
