"""Raw-tree variation capture: per-file variation points of a ``.sysml`` file.

sysmlpy drops every ``variant`` member and every usage-level ``variation`` flag,
but keeps both in the raw parse tree, which
:func:`pyssp_sysml2.model.parser.parse_tree` returns. This module walks that
tree — never ``sysmlpy`` itself — and produces the per-file
:class:`VariationFacts` that :mod:`pyssp_sysml2.model.loader` merges into the
repo-owned model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from pyssp_sysml2.model.model import (
    Attribute,
    Binding,
    Connection,
    PartUsage,
    VariantBody,
    VariantMember,
    endpoint_text,
)
from pyssp_sysml2.model.parser import connection_endpoint, parse_tree


# -- variation points (raw parse tree; see IMP-006) --------------------------


@dataclass
class VariationFacts:
    """Variation captured for one source file, keyed by definition name."""

    variants: dict[str, list[VariantMember]] = field(default_factory=dict)
    attribute_variants: dict[str, list[VariantMember]] = field(default_factory=dict)
    usage_variants: dict[tuple[str, str], list[VariantMember]] = field(
        default_factory=dict
    )
    usage_points: dict[str, set[str]] = field(default_factory=dict)
    attribute_points: set[str] = field(default_factory=set)


def variation_facts(source: str) -> VariationFacts:
    """Recover variation points from the raw parse tree of one file.

    sysmlpy drops every ``variant`` member and every usage-level ``variation``
    flag, but keeps both in the tree: a member is a
    ``VariantUsageElementContext`` with its full text and a usage flag is the
    ``variation`` token in the usage prefix. The walk is deliberately tolerant —
    a shape it does not recognize is skipped, so a parser pin change degrades to
    "not captured" rather than a failed load.
    """
    facts = VariationFacts()
    for node in _tree_nodes(parse_tree(source)):
        try:
            if type(node).__name__ == "VariantUsageElementContext":
                _capture_variant(node, facts)
            elif type(node).__name__ == "PartUsageContext" and _has_variation_prefix(
                node
            ):
                _capture_usage_point(node, facts)
            elif (
                type(node).__name__ == "AttributeDefinitionContext"
                and _has_attribute_variation_prefix(node)
            ):
                _capture_attribute_point(node, facts)
        except (AttributeError, IndexError, TypeError):
            continue
    return facts


def _tree_nodes(node) -> Iterator:
    """Pre-order traversal of a raw ANTLR parse tree."""
    yield node
    for child in getattr(node, "children", None) or []:
        yield from _tree_nodes(child)


def _capture_variant(node, facts: VariationFacts) -> None:
    """Add one variant member to the point that declares it.

    A ``variant part`` belongs either to its enclosing part definition or, when
    the point is a usage, to that usage (keyed by definition and usage name). A
    ``variant attribute`` belongs to an attribute definition. A member declared
    inside another variant's body has no definition owner here; the body walk
    attaches it to the variation usage that declares it.
    """
    if node.partUsage() is not None:
        owner = _variant_owner(node)
        member = _variant_member(node)
        if owner is None or member is None:
            return
        kind, key = owner
        if kind == "definition":
            facts.variants.setdefault(key, []).append(member)
        else:
            facts.usage_variants.setdefault(key, []).append(member)
        return

    if node.attributeUsage() is not None:
        owner = _owning_attribute_definition(node)
        name = _definition_name(owner) if owner is not None else None
        member = _variant_member(node)
        if name is not None and member is not None:
            facts.attribute_variants.setdefault(name, []).append(member)


def _variant_owner(
    node,
) -> tuple[str, str] | tuple[str, tuple[str, str]] | None:
    """Where a ``variant part`` belongs: a definition name or a usage key.

    Returns ``("definition", <PartDefinition name>)`` for a definition-level
    point and ``("usage", (<owning definition>, <usage name>))`` for a
    usage-level point. A member inside a variant body has no enclosing-definition
    owner; :func:`_nested_variants` attaches it to the inner usage instead.
    """
    parent = getattr(node, "parentCtx", None)
    while parent is not None:
        kind = type(parent).__name__
        if kind == "PartDefinitionContext":
            name = _definition_name(parent)
            return ("definition", name) if name is not None else None
        if kind == "PartUsageContext":
            if _inside_variant_body(parent):
                return None
            usage = _usage_name(parent)
            definition = _enclosing_part_definition(parent)
            owner = _definition_name(definition) if definition is not None else None
            if usage is None or owner is None:
                return None
            return ("usage", (owner, usage))
        if kind in {"AttributeDefinitionContext", "AttributeUsageContext"}:
            return None
        parent = getattr(parent, "parentCtx", None)
    return None


def _inside_variant_body(ctx) -> bool:
    """True when *ctx* is itself a variant body, i.e. declared by a variant."""
    parent = getattr(ctx, "parentCtx", None)
    while parent is not None:
        kind = type(parent).__name__
        if kind == "VariantUsageElementContext":
            return True
        if kind == "PartDefinitionContext":
            return False
        parent = getattr(parent, "parentCtx", None)
    return False


def _enclosing_part_definition(ctx):
    """The nearest raw ``PartDefinitionContext`` above *ctx*, or ``None``."""
    parent = getattr(ctx, "parentCtx", None)
    while parent is not None:
        if type(parent).__name__ == "PartDefinitionContext":
            return parent
        parent = getattr(parent, "parentCtx", None)
    return None


def _capture_usage_point(node, facts: VariationFacts) -> None:
    """Record one ``variation part`` usage of its enclosing definition."""
    owner = _owning_part_definition(node)
    definition = _definition_name(owner) if owner is not None else None
    usage = _usage_name(node)
    if definition is None or usage is None:
        return
    facts.usage_points.setdefault(definition, set()).add(usage)


def _capture_attribute_point(node, facts: VariationFacts) -> None:
    """Record one ``variation attribute def`` of this file."""
    name = _definition_name(node)
    if name is not None:
        facts.attribute_points.add(name)


def _owning_part_definition(node):
    """The raw ``PartDefinitionContext`` that owns a node, or ``None``.

    A node inside a usage body has a ``UsageContext`` between it and the
    definition, so it has no definition owner: the variants of a usage-level
    point are not definition variants, and a member of a variant body is not a
    member of the enclosing definition. Both are skipped.
    """
    parent = getattr(node, "parentCtx", None)
    while parent is not None:
        kind = type(parent).__name__
        if kind == "PartDefinitionContext":
            return parent
        if kind in {"UsageContext", "PartUsageContext"}:
            return None
        parent = getattr(parent, "parentCtx", None)
    return None


def _owning_attribute_definition(node):
    """The raw ``AttributeDefinitionContext`` that owns a node, or ``None``.

    Mirrors :func:`_owning_part_definition`: a node inside a usage body has a
    ``UsageContext`` between it and the definition, so a member of a variant
    body is not a member of the enclosing definition.
    """
    parent = getattr(node, "parentCtx", None)
    while parent is not None:
        kind = type(parent).__name__
        if kind == "AttributeDefinitionContext":
            return parent
        if kind in {"UsageContext", "PartUsageContext", "AttributeUsageContext"}:
            return None
        parent = getattr(parent, "parentCtx", None)
    return None


def _definition_name(ctx) -> str | None:
    """Declared name of a raw ``PartDefinitionContext`` or ``AttributeDefinitionContext``."""
    definition = ctx.definition()
    declaration = definition.definitionDeclaration() if definition is not None else None
    identification = declaration.identification() if declaration is not None else None
    return identification.getText() if identification is not None else None


def _usage_name(ctx) -> str | None:
    """Declared name of a raw ``PartUsageContext``, or ``None`` when anonymous."""
    usage = ctx.usage()
    declaration = usage.usageDeclaration() if usage is not None else None
    identification = declaration.identification() if declaration is not None else None
    return identification.getText() if identification is not None else None


def _has_variation_prefix(ctx) -> bool:
    """True when a usage carries the ``variation`` keyword before ``part``."""
    prefix = ctx.occurrenceUsagePrefix()
    basic = prefix.basicUsagePrefix() if prefix is not None else None
    ref = basic.refPrefix() if basic is not None else None
    return ref is not None and ref.VARIATION() is not None


def _has_attribute_variation_prefix(ctx) -> bool:
    """True for a ``variation attribute def`` in the raw tree."""
    prefix = ctx.definitionPrefix()
    basic = prefix.basicDefinitionPrefix() if prefix is not None else None
    return basic is not None and basic.VARIATION() is not None


def _variant_member(node) -> VariantMember | None:
    """Repo VariantMember for one raw ``VariantUsageElementContext``.

    ``variant part`` and ``variant attribute`` are captured; a connect or bind
    variant has neither usage and is skipped. A part variant with a body keeps
    that body's own parts, connections, and bindings.
    """
    usage = node.partUsage()
    kind = "part"
    if usage is None:
        usage = node.attributeUsage()
        kind = "attribute"
    if usage is None:
        return None
    name = _usage_name(usage)
    if name is None:
        return None
    body = _variant_body(usage) if kind == "part" else None
    return VariantMember(
        name=name, kind=kind, type_name=_usage_type(usage), body=body
    )


def _variant_body(usage) -> VariantBody | None:
    """Members declared inside ``variant part name { ... }``, or ``None``.

    The body is the variant usage's own anonymous definition: its direct
    members are part usages, connections, bindings, and attribute usages. A
    part usage may itself be a variation usage; its variant members are kept on
    that usage so a dotted selection can resolve it after the enclosing body is
    selected. A member this walk cannot carry raises ``ValueError`` instead of
    being dropped.
    """
    completion = usage.usage().usageCompletion()
    body = completion.usageBody() if completion is not None else None
    definition_body = body.definitionBody() if body is not None else None
    if definition_body is None:
        return None

    captured = VariantBody()
    for item in _as_list(definition_body.children):
        if type(item).__name__ != "DefinitionBodyItemContext":
            continue
        if _is_variant_member_item(item):
            # A nested member of the enclosing point, captured by
            # _capture_variant (part) or skipped (attribute/connect/bind).
            continue
        if _is_comment_item(item):
            continue
        part = _first_descendant(item, "PartUsageContext")
        if part is not None:
            name = _usage_name(part)
            if name is None:
                raise ValueError(
                    "A part usage in a variant body must be named"
                )
            _reject_body_decomposition(part, name)
            captured.parts[name] = PartUsage(
                name=name,
                type_name=_usage_type(part),
                is_variation=_has_variation_prefix(part),
                variants=_nested_variants(part),
            )
            continue
        connect = _first_descendant(item, "ConnectionUsageContext")
        if connect is not None:
            connection = _raw_connection(connect)
            captured.connections[connection.key] = connection
            continue
        bind = _first_descendant(item, "BindingConnectorAsUsageContext")
        if bind is not None:
            captured.bindings.append(_raw_binding(bind))
            continue
        attribute = _first_descendant(item, "AttributeUsageContext")
        if attribute is not None:
            name = _usage_name(attribute)
            if name is None:
                raise ValueError(
                    "An attribute usage in a variant body must be named"
                )
            if "=" in attribute.getText():
                raise ValueError(
                    f"Attribute usage '{name}' in a variant body declares a "
                    "value; body attributes carry a type only. Declare the "
                    "value on the attribute definition instead."
                )
            captured.attributes[name] = Attribute(
                name=name, type_name=_usage_type(attribute)
            )
            continue
        if _has_content(item):
            raise ValueError(
                "Unsupported member in a variant body: "
                f"'{item.getText().strip()}'. A body carries parts, "
                "connections, bindings, and attribute usages."
            )
    if not (
        captured.parts
        or captured.connections
        or captured.bindings
        or captured.attributes
    ):
        return None
    return captured


def _is_variant_member_item(item) -> bool:
    """True when a body item declares a ``variant`` member of the body's point."""
    for child in getattr(item, "children", None) or []:
        if type(child).__name__ != "DefinitionBodyItemContentContext":
            continue
        for content in getattr(child, "children", None) or []:
            if type(content).__name__ == "TerminalNodeImpl":
                return content.getText() == "variant"
    return False


def _nested_variants(usage) -> list[VariantMember]:
    """Variant members declared directly by a variation usage inside a body."""
    completion = usage.usage().usageCompletion()
    body = completion.usageBody() if completion is not None else None
    definition_body = body.definitionBody() if body is not None else None
    if definition_body is None:
        return []
    members: list[VariantMember] = []
    for item in _as_list(definition_body.children):
        if type(item).__name__ != "DefinitionBodyItemContext":
            continue
        if not _is_variant_member_item(item):
            continue
        element = _first_descendant(item, "VariantUsageElementContext")
        member = _variant_member(element) if element is not None else None
        if member is not None:
            members.append(member)
    return members


def _reject_body_decomposition(usage, name: str) -> None:
    """Reject a body part that declares its own members instead of a type."""
    completion = usage.usage().usageCompletion()
    body = completion.usageBody() if completion is not None else None
    definition_body = body.definitionBody() if body is not None else None
    if definition_body is None:
        return
    for item in _as_list(definition_body.children):
        if type(item).__name__ == "DefinitionBodyItemContext" and not (
            _is_variant_member_item(item) or _is_comment_item(item)
        ):
            raise ValueError(
                f"Part usage '{name}' in a variant body declares its own "
                "members; nested decomposition inside a variant body is not "
                "supported. Give the part a type or flatten it."
            )


def _is_comment_item(item) -> bool:
    """True when a body item is only a ``/* ... */`` doc comment."""
    text = item.getText().strip()
    return text.startswith("/*") and text.endswith("*/")


def _has_content(item) -> bool:
    """True when a body item carries more than a lone ``;`` terminator."""
    text = item.getText().strip()
    return bool(text and text != ";")


def _first_descendant(node, kind: str):
    """First descendant context of *kind* below *node*, pre-order, or ``None``."""
    for child in getattr(node, "children", None) or []:
        if type(child).__name__ == kind:
            return child
        found = _first_descendant(child, kind)
        if found is not None:
            return found
    return None


def _raw_connection(ctx) -> Connection:
    """Repo Connection from a raw ``ConnectionUsageContext`` in a variant body."""
    connector_part = ctx.connectorPart()
    binary = (
        connector_part.binaryConnectorPart()
        if connector_part is not None
        else None
    )
    ends = (
        [
            _raw_end_names(end)
            for end in _as_list(binary.children)
            if type(end).__name__ == "ConnectorEndMemberContext"
        ]
        if binary is not None
        else []
    )
    if len(ends) != 2:
        raise ValueError(
            "Only binary connections are supported "
            "('connect a.p to b.q;'), got "
            f"{len(ends)} ends in a variant body"
        )
    source_part, source_port = connection_endpoint(ends[0])
    destination_part, destination_port = connection_endpoint(ends[1])
    return Connection(
        name=(
            f"{endpoint_text(source_part, source_port)}"
            f"_to_{endpoint_text(destination_part, destination_port)}"
        ),
        source_part=source_part,
        source_port=source_port,
        destination_part=destination_part,
        destination_port=destination_port,
    )


def _raw_binding(ctx) -> Binding:
    """Repo Binding from a raw ``BindingConnectorAsUsageContext``."""
    ends = [_raw_end_names(end) for end in _as_list(ctx.connectorEndMember())]
    if len(ends) != 2 or not ends[0] or not ends[1]:
        raise ValueError(
            "Binding ends must be feature references "
            "('bind a.x = b.y;'), got a malformed bind in a variant body"
        )
    return Binding(source=tuple(ends[0]), target=tuple(ends[1]))


def _raw_end_names(end_member) -> list[str]:
    """Feature-chain names of one raw ``ConnectorEndMemberContext``.

    Mirrors :func:`_end_names`, which reads sysmlpy wrapper objects; the body
    walk has only raw contexts, where a dotted chain is a list of
    ``QualifiedNameContext`` children.
    """
    names: list[str] = []
    for end in _as_list(getattr(end_member, "children", None)):
        if type(end).__name__ != "ConnectorEndContext":
            continue
        for subsetting in _as_list(getattr(end, "children", None)):
            if type(subsetting).__name__ != "OwnedReferenceSubsettingContext":
                continue
            for qualified in _as_list(subsetting.qualifiedName()):
                names.append(qualified.getText())
    return names


def _usage_type(ctx) -> str | None:
    """Declared type of a raw part or attribute usage as written, or ``None``."""
    usage = ctx.usage()
    declaration = usage.usageDeclaration() if usage is not None else None
    specialization = (
        declaration.featureSpecializationPart() if declaration is not None else None
    )
    if specialization is None:
        return None
    for feature in _as_list(specialization.featureSpecialization()):
        typings = feature.typings()
        typed_by = typings.typedBy() if typings is not None else None
        for typing in _as_list(
            typed_by.featureTyping() if typed_by is not None else None
        ):
            return typing.getText()
    return None


def _as_list(value) -> list:
    """ANTLR accessors return a context or a list of them; normalize to a list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]
