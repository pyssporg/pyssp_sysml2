"""sysmlpy-backed loader: builds the repo-owned model from ``.sysml`` files.

This is the ONLY module in the repo that imports `sysmlpy` (0.96.4). It
converts parsed files into the dataclasses of
:mod:`pyssp_sysml2.model.model` and merges them into one
:class:`~pyssp_sysml2.model.model.Architecture`; every other module
works against that repo-owned model, never against sysmlpy objects.

sysmlpy quirks compensated here (verified in the migration notes,
``sysmlpy_api.md`` §§4-6, 9-10):

- port directions and connection endpoints exist only in the grammar
  layer, so both are extracted by dedicated walks (see the
  "Grammar-layer walks" section at the bottom — swap these first when a
  future sysmlpy release exposes the data publicly);
- ``attribute b = true;`` yields the *string* ``'true'`` and tuples yield
  raw ``'(1.0,2.0)'`` text, so values are normalized back to Python
  literals (legacy ``pycps_sysmlv2`` §5.5 semantics);
- ``get_value()`` raises ``AttributeError`` for value-less attributes and
  drops the sign of negative number literals (``-1.5`` reads as ``1.5``);
- unnamed ``connect`` statements get a UUID as their name, so the legacy
  ``"{src}.{src_port}_to_{dst}.{dst_port}"`` name is rebuilt for them;
- ``variant`` members, usage-level ``variation`` flags, and ``variation
  attribute def`` flags never reach the parsed model, so all are recovered from
  the raw parse tree (``_variation_facts``); the tree is a sysmlpy internal and
  is read here only.

Loading stays non-validating: ``resolve_types()``/``analyze()`` are never
called, so unresolved references simply surface as ``resolve_part``/
``resolve_port`` returning ``None`` in consumers.
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import sysmlpy

from pyssp_sysml2.model.model import (
    Architecture,
    Attribute,
    AttributeDefinition,
    Binding,
    Connection,
    PartDefinition,
    PartUsage,
    PortDefinition,
    PortUsage,
    RequirementDefinition,
    VariantBody,
    VariantMember,
    endpoint_text,
)

__all__ = ["load"]

# sysmlpy tries to persist its ANTLR DFA cache on the first parse of a
# process; on this machine (Python 3.10) that pickling hits a RecursionError,
# so sysmlpy emits a one-time, benign "DFA cache save failed" UserWarning and
# continues without the cache. Suppress it here once instead of letting it
# leak into every caller's stderr (sysmlpy_api.md §9).
warnings.filterwarnings("ignore", message="DFA cache", category=UserWarning)

# sysmlpy names unnamed `connect` statements with a UUID string.
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def load(path: Path | str) -> Architecture:
    """Load a ``.sysml`` file or a directory of them into an Architecture.

    A file loads exactly that file; a directory loads its ``*.sysml`` files
    non-recursively in sorted name order, and every file must declare the
    same package. Each file is parsed by sysmlpy separately (never as one
    merged multi-file load) so definitions keep per-file ``source_file``
    tracking and cross-file duplicates can be reported precisely.
    """
    files = _resolve_files(Path(path))
    architecture = _architecture_from(files[0])
    for file in files[1:]:
        _merge_file(architecture, file)
    return architecture


# -- file resolution (legacy parity) --------------------------------------


def _resolve_files(path: Path) -> list[Path]:
    """Resolve a load target to the files to parse, matching legacy semantics.

    File → ``[path]``; directory → non-recursive ``sorted(glob("*.sysml"))``;
    a missing path or an empty directory raise ``FileNotFoundError`` (the
    missing-path message is what ``sync.py`` catches to bootstrap from SSD).
    """
    if path.is_file():
        return [path]
    if path.is_dir():
        files = sorted(path.glob("*.sysml"))
        if not files:
            raise FileNotFoundError(f"No .sysml files found under {path}")
        return files
    raise FileNotFoundError(f"No .sysml file found under {path}")


# -- per-file loading and merging ------------------------------------------


def _architecture_from(file: Path) -> Architecture:
    """Build a fresh Architecture from the first file of a load."""
    packages, variation = _parse_file(file)
    architecture = Architecture(package_name=packages[0].name)
    _merge_packages(architecture, packages, file, variation)
    return architecture


def _merge_file(architecture: Architecture, file: Path) -> None:
    """Merge one more file into ``architecture`` (package names must match)."""
    packages, variation = _parse_file(file)
    name = packages[0].name
    if name != architecture.package_name:
        raise ValueError(
            f"Mismatched package names: {architecture.package_name} vs {name} in {file}"
        )
    _merge_packages(architecture, packages, file, variation)


def _parse_file(file: Path) -> tuple[list, _VariationFacts]:
    """Parse one file: its package(s), plus variation facts from the raw tree.

    sysmlpy's ``load_files`` parses a single file into a Model whose direct
    children are the file's top-level ``package`` declarations; everything
    the repo supports lives in exactly one same-named package per file.

    The source text is read once here: ``load_files`` takes the path, and the
    raw-tree walk takes the text, so variation capture adds a parse pass but no
    second read.
    """
    source = file.read_text(encoding="utf-8")
    model = sysmlpy.load_files([str(file)])
    names = sorted({package.name for package in model.packages})
    if not names:
        raise ValueError(f"No package declaration found in {file}")
    if len(names) > 1:
        raise ValueError(f"Expected one package per file, found {', '.join(names)} in {file}")
    return list(model.packages), _variation_facts(source)


def _merge_packages(
    architecture: Architecture,
    packages: list,
    file: Path,
    variation: _VariationFacts,
) -> None:
    """Add every definition of one file's package(s) to the architecture.

    Top-level usages and other non-definition children are skipped silently
    (legacy parity). Definitions are added parts first, then ports, then
    attribute definitions, then requirements — the retired parser's assembly
    order extended with value types.
    """
    for package in packages:
        for element in package.parts:
            if element.is_definition:
                part_def = _part_definition(element, file, variation)
                _add_definition(architecture, architecture.add_part_def, part_def, file)
        for element in package.ports:
            if element.is_definition:
                port_def = _port_definition(element, file)
                _add_definition(architecture, architecture.add_port_def, port_def, file)
        for element in package.attributes:
            if element.is_definition:
                attribute_def = _attribute_definition(element, file, variation)
                _add_definition(
                    architecture, architecture.add_attribute_def, attribute_def, file
                )
        for element in package.requirements:
            if element.is_definition:
                requirement_def = _requirement_definition(element, file)
                _add_definition(
                    architecture, architecture.add_requirement_def, requirement_def, file
                )


def _add_definition(architecture: Architecture, add, definition, file: Path) -> None:
    """Add a definition, re-raising duplicates with file context (legacy parity)."""
    try:
        add(definition)
    except ValueError:
        kind = type(definition).__name__.removesuffix("Definition").lower()
        raise ValueError(f"Duplicate {kind} definition for {definition.name} in {file}") from None


# -- definition builders ----------------------------------------------------


def _part_definition(element, file: Path, variation: _VariationFacts) -> PartDefinition:
    """Repo PartDefinition from a sysmlpy part definition.

    Member docs are not captured: sysmlpy attaches a ``doc /* ... */``
    written above a member to the owning definition, so per-member docs are
    not recoverable from a parsed model (sysmlpy_api.md §3).

    The variation flag comes from the grammar prefix; the variant members and
    usage-level flags come from the raw-tree walk, keyed by this definition's
    name.
    """
    part_def = PartDefinition(
        name=element.name,
        doc=element.doc,
        source_file=file.name,
        specializes=_specializes(element),
        is_variation=_is_definition_variation(element),
        variants=list(variation.variants.get(element.name, ())),
    )
    variation_usages = variation.usage_points.get(element.name, ())
    for attribute in element.attributes:
        part_def.attributes[attribute.name] = _attribute(attribute)
    for port in element.ports:
        # A redefining port (``out port :>> y : T;``) gets a UUID as its parsed
        # name; ``display_name`` keeps the name the composition connects to.
        name = getattr(port, "display_name", None) or port.name
        part_def.ports[name] = PortUsage(
            name=name,
            direction=_port_direction(port),
            type_name=port.typed_by_name,
        )
    for part in element.parts:
        part_def.parts[part.name] = PartUsage(
            name=part.name,
            type_name=part.typed_by_name,
            is_variation=part.name in variation_usages,
            variants=list(
                variation.usage_variants.get((element.name, part.name), ())
            ),
        )
    for connect in element.connections:
        connection = _connection(connect, file)
        # Keyed by endpoint pair: a later connect with identical endpoints
        # overwrites the earlier one (legacy parity).
        part_def.connections[connection.key] = connection
    for child in element.children:
        if type(child).__name__ == "Binding":
            part_def.bindings.append(_binding(child, file))
    return part_def


def _port_definition(element, file: Path) -> PortDefinition:
    """Repo PortDefinition from a sysmlpy port definition."""
    port_def = PortDefinition(
        name=element.name,
        doc=element.doc,
        source_file=file.name,
        specializes=_specializes(element),
    )
    for attribute in element.attributes:
        port_def.attributes[attribute.name] = _attribute(attribute)
    return port_def


def _attribute_definition(
    element, file: Path, variation: _VariationFacts
) -> AttributeDefinition:
    """Repo AttributeDefinition from a sysmlpy attribute definition."""
    attribute_def = AttributeDefinition(
        name=element.name,
        doc=element.doc,
        source_file=file.name,
        specializes=_specializes(element),
        is_variation=element.name in variation.attribute_points,
        variants=list(variation.attribute_variants.get(element.name, ())),
    )
    for attribute in element.attributes:
        attribute_def.attributes[attribute.name] = _attribute(attribute)
    return attribute_def


def _requirement_definition(element, file: Path) -> RequirementDefinition:
    """Repo RequirementDefinition; the doc comment is the requirement text."""
    return RequirementDefinition(name=element.name, text=element.doc, source_file=file.name)


def _connection(connect, file: Path) -> Connection:
    """Repo Connection from a sysmlpy connect statement.

    Only binary connects are supported. An end is either part-qualified
    (``connect a.p to b.q;``) or a bare port name that refers to a port of the
    enclosing part def, i.e. the system boundary (``connect gain.y to y;``).
    A parsed name of ``None`` or a UUID means sysmlpy generated it for an
    unnamed connect, so the legacy endpoint-derived name is rebuilt instead.
    """
    ends = _connection_endpoints(connect)
    if len(ends) != 2:
        raise ValueError(
            f"Only binary connections are supported ('connect a.p to b.q;'), "
            f"got {len(ends)} ends in {file}"
        )
    source, destination = ends
    source_part, source_port = _connection_endpoint(source, file)
    destination_part, destination_port = _connection_endpoint(destination, file)
    name = connect.name
    if name is None or _UUID_PATTERN.match(name):
        name = (
            f"{endpoint_text(source_part, source_port)}"
            f"_to_{endpoint_text(destination_part, destination_port)}"
        )
    return Connection(
        name=name,
        source_part=source_part,
        source_port=source_port,
        destination_part=destination_part,
        destination_port=destination_port,
    )


def _connection_endpoint(
    names: list[str], file: Path | None = None
) -> tuple[str | None, str]:
    """Split one connection end into ``(part, port)``; a bare name is a boundary port."""
    if not names:
        where = f" in {file}" if file is not None else " in a variant body"
        raise ValueError(
            "Connection ends must be 'part.port' or a boundary 'port', "
            f"got an empty end{where}"
        )
    if len(names) == 1:
        return None, names[0]
    return names[0], names[-1]


def _binding(bind, file: Path) -> Binding:
    """Repo Binding from a sysmlpy ``bind a.x = b.y;`` statement.

    Both endpoints keep their full feature chain. Unnamed bindings receive a
    UUID name from sysmlpy; those are normalized back to ``None``.
    """
    ends = _binding_endpoints(bind)
    if len(ends) != 2:
        raise ValueError(
            f"Only binary bindings are supported ('bind a.x = b.y;'), "
            f"got {len(ends)} ends in {file}"
        )
    source, target = ends
    if not source or not target:
        raise ValueError(
            f"Binding ends must be feature references, got {source} = {target} in {file}"
        )
    name = bind.name
    if name is None or _UUID_PATTERN.match(name):
        name = None
    return Binding(source=tuple(source), target=tuple(target), name=name)


# -- attribute values (legacy §5.5 semantics) -------------------------------


def _attribute(element) -> Attribute:
    """Repo Attribute from a sysmlpy attribute usage."""
    return Attribute(
        name=element.name,
        type_name=element.typed_by_name,
        value=_normalize_value(element),
        multiplicity=_multiplicity(element),
    )


def _normalize_value(element) -> object:
    """sysmlpy value → Python-native value, bool check first (legacy §5.5).

    ``get_value()`` raises ``AttributeError`` for value-less attributes
    (``attribute x;``), returns strings for ``true``/tuples, and pint
    ``Quantity`` objects for unit literals — all normalized here.
    """
    try:
        value = element.get_value()
    except AttributeError:
        return None  # value-less attribute
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return _with_literal_sign(element, value)
    if isinstance(value, str):
        return _normalize_string(value)
    if hasattr(value, "magnitude"):  # pint Quantity, e.g. `1000 [kilogram]`
        return _with_literal_sign(element, value.magnitude)
    return value


def _with_literal_sign(element, value):
    """Negate ``value`` when its source literal had a leading minus.

    sysmlpy 0.96.4's ``get_value()`` ignores the unary minus of negative
    number literals (``-1.5`` comes back as ``1.5``), so the sign is
    re-attached from the grammar layer.
    """
    return -value if _literal_is_negative(element) else value


def _normalize_string(text: str):
    """String value from sysmlpy → Python value.

    ``'true'``/``'false'`` → bool (case-insensitive, as in the legacy
    parser); text wrapped in parentheses → tuple of parsed scalars;
    anything else → the string itself with escape sequences decoded.
    """
    lowered = text.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    if text.startswith("(") and text.endswith(")"):
        return _parse_tuple(text[1:-1])
    return _decode_escapes(text)


def _parse_tuple(inner: str):
    """Comma-separated tuple body → tuple of scalars.

    A single element without a comma is a plain parenthesized scalar
    (``(1.0)`` → ``1.0``), matching the legacy ``ast.literal_eval`` behavior.
    """
    items = _split_top_level(inner)
    if len(items) == 1:
        return _parse_scalar(items[0])
    return tuple(_parse_scalar(item) for item in items)


def _split_top_level(text: str) -> list[str]:
    """Split tuple body on commas, ignoring commas inside quoted strings."""
    items: list[str] = []
    current: list[str] = []
    quoted = False
    escaped = False
    for char in text:
        if escaped:
            current.append(char)
            escaped = False
        elif quoted and char == "\\":
            current.append(char)
            escaped = True
        elif char == '"':
            quoted = not quoted
            current.append(char)
        elif char == "," and not quoted:
            items.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    items.append("".join(current).strip())
    return items


def _parse_scalar(text: str):
    """One tuple element → bool/int/float/str (quoted strings unquoted)."""
    if len(text) >= 2 and text.startswith('"') and text.endswith('"'):
        return _decode_escapes(text[1:-1])
    lowered = text.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            continue
    return text


_STRING_ESCAPES = {
    "\\": "\\",
    '"': '"',
    "'": "'",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}


def _decode_escapes(text: str) -> str:
    r"""Decode the escapes supported in SysML string literals.

    sysmlpy keeps string escape sequences raw, so the adapter decodes them
    without evaluating the literal as Python source. The set covers the escapes
    the exporter emits plus the standard single-character escapes, so a value
    round-trips on every pass.
    """
    return re.sub(
        r"\\([\\\"'nrt])",
        lambda match: _STRING_ESCAPES[match.group(1)],
        text,
    )


# -- grammar-layer walks (sysmlpy internals; swap here on a future release) --


def _is_definition_variation(element) -> bool:
    """True for a ``variation part def``: a definition-level variation point.

    sysmlpy keeps the keyword but no dataclass exposes it; it sits in the
    definition prefix as ``PartDefinition.prefix`` (``OccurrenceDefinitionPrefix``)
    → ``prefix`` (``BasicDefinitionPrefix``) → ``isVariation == "variation"``.
    """
    prefix = getattr(element.grammar, "prefix", None)  # OccurrenceDefinitionPrefix
    prefix = getattr(prefix, "prefix", None) if prefix else None  # BasicDefinitionPrefix
    return getattr(prefix, "isVariation", None) == "variation"


def _port_direction(port) -> str | None:
    """'in' | 'out' | 'inout' | None for a parsed port usage.

    sysmlpy 0.96.4 exposes no public direction attribute; it is preserved in
    the grammar as ``PortUsage.prefix`` → ``OccurrenceUsagePrefix`` →
    ``BasicUsagePrefix`` → ``RefPrefix`` → ``FeatureDirection``. ``None``
    means an undirected port (``port p : S;``) and stays ``None``.
    """
    prefix = getattr(port.grammar, "prefix", None)  # OccurrenceUsagePrefix
    prefix = getattr(prefix, "prefix", None) if prefix else None  # BasicUsagePrefix
    prefix = getattr(prefix, "prefix", None) if prefix else None  # RefPrefix
    direction = getattr(prefix, "direction", None) if prefix else None  # FeatureDirection
    if direction is None:
        return None
    if getattr(direction, "isInOut", False):
        return "inout"
    if getattr(direction, "isIn", False):
        return "in"
    if getattr(direction, "isOut", False):
        return "out"
    return None


def _end_names(end_member) -> list[str]:
    """Feature-chain names of one ``ConnectorEndMember``.

    Both ``connect`` and ``bind`` ends use the same shape:
    ``ConnectorEndMember`` → ``.children`` (``ConnectorEnd``) → ``.children``
    (``OwnedReferenceSubsetting``) → ``referencedFeature`` / ``elements``
    (``OwnedFeatureChain`` → ``OwnedFeatureChaining``). A bare feature uses
    ``referencedFeature``; a dotted chain uses the ``elements`` list.
    """
    names: list[str] = []
    for connector_end in getattr(end_member, "children", []):  # ConnectorEnd
        for subsetting in connector_end.children:
            if type(subsetting).__name__ != "OwnedReferenceSubsetting":
                continue  # OwnedMultiplicity etc.
            if subsetting.referencedFeature is not None:
                names.extend(subsetting.referencedFeature.names)
            for chain in subsetting.elements:  # OwnedFeatureChain
                for chaining in chain.feature.children:  # OwnedFeatureChaining
                    names.extend(chaining.chainingFeature.names)
    return names


def _connection_endpoints(connect) -> list[list[str]]:
    """Per-end feature chains of a connect, e.g. ``[['src', 'sig'], ['dst', 'sigIn']]``.

    sysmlpy 0.96.4 exposes no public endpoint accessors; the ends live in
    the grammar as ``ConnectionUsage.part`` (``ConnectorPart``) → ``.part``
    (``BinaryConnectorPart``) → ``.children`` (``ConnectorEndMember``).
    """
    grammar = connect.grammar  # ConnectionUsage
    connector_part = getattr(grammar, "part", None)  # ConnectorPart
    binary = getattr(connector_part, "part", None) if connector_part else None
    if binary is None:
        return []
    return [_end_names(end_member) for end_member in binary.children]


def _binding_endpoints(bind) -> list[list[str]]:
    """Per-end feature chains of a ``bind`` statement (``BindingConnector``)."""
    grammar = bind.grammar  # BindingConnector
    return [_end_names(end_member) for end_member in grammar.children]


def _specializes(element) -> tuple[str, ...]:
    """Declared supertypes of a definition (``:> A, B``), in source order."""
    try:
        part = element.grammar.definition.declaration.subclassificationpart
    except AttributeError:
        return ()
    if part is None:
        return ()
    names: list[str] = []
    for subclassification in getattr(part, "children", []):
        qualified = getattr(subclassification, "name", None)
        if qualified is not None:
            names.extend(qualified.names)
    return tuple(names)


def _multiplicity(element) -> str | None:
    """Declared multiplicity range of an attribute, e.g. ``"3"`` or ``"0..*"``.

    sysmlpy exposes the range only in the grammar:
    ``FeatureSpecializationPart.multiplicity`` (``MultiplicityPart``) →
    ``.children`` (``OwnedMultiplicity``) → ``.children``
    (``MultiplicityRange``) → ``.children`` (``MultiplicityExpressionMember``)
    → ``.children[0].element`` (``LiteralInteger`` / ``LiteralInfinity``).
    """
    try:
        specialization = element.grammar.usage.declaration.declaration.specialization
        multiplicity = specialization.multiplicity
    except AttributeError:
        return None
    if multiplicity is None:
        return None

    bounds: list[str] = []
    for owned in getattr(multiplicity, "children", []):
        for range_ in getattr(owned, "children", []):
            for member in getattr(range_, "children", []):
                elements = getattr(member, "children", [])
                if not elements:
                    continue
                literal = getattr(elements[0], "element", None)
                value = getattr(literal, "element", None)
                if value is not None:
                    bounds.append(str(value))
    if not bounds:
        return None
    if len(bounds) == 1:
        return bounds[0]
    return "..".join(bounds)


def _literal_is_negative(element) -> bool:
    """True when the attribute's number literal has a leading minus.

    The sign survives only in the grammar's ``UnaryExpression.operator``
    (``get_value()`` ignores it), reached through the same expression chain
    ``get_value()`` itself walks.
    """
    try:
        unary = (
            element.grammar.usage.completion.valuepart.relationships[0]
            .element.expression.operands[0]
            .implies.orexpression.xor.andexpression.equality.classification.relational.range
            .additive.left_hand.exponential.unary
        )
    except (AttributeError, IndexError, TypeError):
        return False
    return getattr(unary, "operator", None) == "-"


# -- variation points (raw parse tree; see IMP-006) --------------------------


@dataclass
class _VariationFacts:
    """Variation captured for one source file, keyed by definition name."""

    variants: dict[str, list[VariantMember]] = field(default_factory=dict)
    attribute_variants: dict[str, list[VariantMember]] = field(default_factory=dict)
    usage_variants: dict[tuple[str, str], list[VariantMember]] = field(
        default_factory=dict
    )
    usage_points: dict[str, set[str]] = field(default_factory=dict)
    attribute_points: set[str] = field(default_factory=set)


def _variation_facts(source: str) -> _VariationFacts:
    """Recover variation points from the raw parse tree of one file.

    sysmlpy drops every ``variant`` member and every usage-level ``variation``
    flag, but keeps both in the tree: a member is a
    ``VariantUsageElementContext`` with its full text and a usage flag is the
    ``variation`` token in the usage prefix. The walk is deliberately tolerant —
    a shape it does not recognize is skipped, so a parser pin change degrades to
    "not captured" rather than a failed load.
    """
    facts = _VariationFacts()
    for node in _tree_nodes(sysmlpy.antlr_parser.parse(source)):
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


def _capture_variant(node, facts: _VariationFacts) -> None:
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


def _capture_usage_point(node, facts: _VariationFacts) -> None:
    """Record one ``variation part`` usage of its enclosing definition."""
    owner = _owning_part_definition(node)
    definition = _definition_name(owner) if owner is not None else None
    usage = _usage_name(node)
    if definition is None or usage is None:
        return
    facts.usage_points.setdefault(definition, set()).add(usage)


def _capture_attribute_point(node, facts: _VariationFacts) -> None:
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
    source_part, source_port = _connection_endpoint(ends[0])
    destination_part, destination_port = _connection_endpoint(ends[1])
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
