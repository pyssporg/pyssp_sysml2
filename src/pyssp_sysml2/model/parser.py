"""sysmlpy boundary: parsed packages, raw trees, and grammar-layer extras.

This is the ONLY module in the repo that imports `sysmlpy` (0.96.4) and the only
one that parses a raw ANTLR tree. It hands the rest of
:mod:`pyssp_sysml2.model` three things:

- :func:`parse_packages` — the ``package`` declarations of one file;
- :func:`parse_tree` — the raw parse tree of one source text;
- the grammar-layer walks and value normalizers that
  :mod:`pyssp_sysml2.model.loader` builds the repo-owned model from.

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
  ``"{src}.{src_port}_to_{dst}.{dst_port}"`` name is rebuilt for them.

Loading stays non-validating: ``resolve_types()``/``analyze()`` are never
called, so unresolved references simply surface as ``resolve_part``/
``resolve_port`` returning ``None`` in consumers.
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path

import sysmlpy


# sysmlpy tries to persist its ANTLR DFA cache on the first parse of a
# process; on this machine (Python 3.10) that pickling hits a RecursionError,
# so sysmlpy emits a one-time, benign "DFA cache save failed" UserWarning and
# continues without the cache. Suppress it here once instead of letting it
# leak into every caller's stderr (sysmlpy_api.md §9).
warnings.filterwarnings("ignore", message="DFA cache", category=UserWarning)

# sysmlpy names unnamed `connect` statements with a UUID string.
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


# -- package and tree loading (the sysmlpy contact point) -------------------


def parse_packages(path: Path | str) -> list:
    """The top-level ``package`` declarations of one ``.sysml`` file.

    sysmlpy's ``load_files`` parses a single file into a Model whose direct
    children are the file's top-level ``package`` declarations; everything the
    repo supports lives in exactly one same-named package per file.
    """
    file = Path(path)
    model = sysmlpy.load_files([str(file)])
    names = sorted({package.name for package in model.packages})
    if not names:
        raise ValueError(f"No package declaration found in {file}")
    if len(names) > 1:
        raise ValueError(f"Expected one package per file, found {', '.join(names)} in {file}")
    return list(model.packages)


def parse_tree(source: str):
    """Raw ANTLR parse tree of one source text (a sysmlpy internal)."""
    return sysmlpy.antlr_parser.parse(source)


# -- connection endpoints ---------------------------------------------------


def connection_endpoint(
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


# -- attribute values (legacy §5.5 semantics) -------------------------------


def normalize_value(element) -> object:
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


def is_definition_variation(element) -> bool:
    """True for a ``variation part def``: a definition-level variation point.

    sysmlpy keeps the keyword but no dataclass exposes it; it sits in the
    definition prefix as ``PartDefinition.prefix`` (``OccurrenceDefinitionPrefix``)
    → ``prefix`` (``BasicDefinitionPrefix``) → ``isVariation == "variation"``.
    """
    prefix = getattr(element.grammar, "prefix", None)  # OccurrenceDefinitionPrefix
    prefix = getattr(prefix, "prefix", None) if prefix else None  # BasicDefinitionPrefix
    return getattr(prefix, "isVariation", None) == "variation"


def port_direction(port) -> str | None:
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


def connection_endpoints(connect) -> list[list[str]]:
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


def binding_endpoints(bind) -> list[list[str]]:
    """Per-end feature chains of a ``bind`` statement (``BindingConnector``)."""
    grammar = bind.grammar  # BindingConnector
    return [_end_names(end_member) for end_member in grammar.children]


def specializes(element) -> tuple[str, ...]:
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


def multiplicity(element) -> str | None:
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
