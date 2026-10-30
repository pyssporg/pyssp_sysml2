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

from pyssp_sysml2.model.model import ConstraintParameter, ConstraintUsage


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


# -- constraint bodies ------------------------------------------------------
#
# ``grammar.dump()`` is reliable for constraint *usages* but garbles the
# expression of a constraint *definition*. Definitions are therefore read from
# the authored source text, once per file, by scanning the matching braces.

_CONSTRAINT_DEF = re.compile(r"\bconstraint\s+def\s+([A-Za-z_]\w*)\s*\{")
_IN_PARAMETER = re.compile(r"^in\s+([A-Za-z_]\w*)\s*:\s*([\w:]+)$")
_IN_BINDING = re.compile(r"^in\s+([A-Za-z_]\w*)\s*=\s*(.+)$")
_DOC_STRING = re.compile(r'\bdoc\s*"(?:\\.|[^"\\])*"')


def _mask_ignored(text: str) -> str:
    """Blank comments and string literals, preserving offsets and newlines."""
    chars = list(text)
    index = 0
    length = len(text)
    while index < length:
        if text.startswith("//", index):
            end = text.find("\n", index)
            end = length if end == -1 else end
            for position in range(index, end):
                chars[position] = " "
            index = end
        elif text.startswith("/*", index):
            end = text.find("*/", index + 2)
            end = length if end == -1 else end + 2
            for position in range(index, end):
                if chars[position] != "\n":
                    chars[position] = " "
            index = end
        elif text[index] == '"':
            end = index + 1
            escaped = False
            while end < length:
                if escaped:
                    escaped = False
                elif text[end] == "\\":
                    escaped = True
                elif text[end] == '"':
                    end += 1
                    break
                end += 1
            for position in range(index, end):
                if chars[position] != "\n":
                    chars[position] = " "
            index = end
        else:
            index += 1
    return "".join(chars)


def _matching_brace(text: str, opening: int) -> int:
    """Index of the ``}`` matching the ``{`` at *opening* in masked text."""
    depth = 0
    for index in range(opening, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("Unbalanced '{' in constraint body")


def constraint_definitions_from_source(source: str) -> dict[str, str]:
    """Authored body text of every ``constraint def Name { ... }``, keyed by name."""
    masked = _mask_ignored(source)
    bodies: dict[str, str] = {}
    for match in _CONSTRAINT_DEF.finditer(masked):
        opening = match.end() - 1
        closing = _matching_brace(masked, opening)
        bodies[match.group(1)] = source[opening + 1 : closing]
    return bodies


def constraint_definition_body(source: str, name: str) -> str | None:
    """Authored body of the named constraint definition, or ``None``."""
    return constraint_definitions_from_source(source).get(name)


def _remove_comments(text: str) -> str:
    """Drop ``//`` and ``/* ... */`` comments, keeping everything else."""
    chars = list(text)
    index = 0
    length = len(text)
    while index < length:
        if text.startswith("//", index):
            end = text.find("\n", index)
            end = length if end == -1 else end
            for position in range(index, end):
                chars[position] = " "
            index = end
        elif text.startswith("/*", index):
            end = text.find("*/", index + 2)
            end = length if end == -1 else end + 2
            for position in range(index, end):
                if chars[position] != "\n":
                    chars[position] = " "
            index = end
        elif text[index] == '"':
            end = index + 1
            escaped = False
            while end < length:
                if escaped:
                    escaped = False
                elif text[end] == "\\":
                    escaped = True
                elif text[end] == '"':
                    end += 1
                    break
                end += 1
            index = end
        else:
            index += 1
    return "".join(chars)


def _split_statements(text: str) -> list[str]:
    """Split a body on top-level ``;``, respecting parentheses and strings."""
    statements: list[str] = []
    current: list[str] = []
    depth = 0
    quoted = False
    escaped = False
    for char in text:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if quoted and char == "\\":
            current.append(char)
            escaped = True
            continue
        if char == '"':
            quoted = not quoted
            current.append(char)
            continue
        if not quoted:
            if char in "([{":
                depth += 1
            elif char in ")]}":
                depth = max(depth - 1, 0)
            elif char == ";" and depth == 0:
                statements.append("".join(current).strip())
                current = []
                continue
        current.append(char)
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return [statement for statement in statements if statement]


def parse_constraint_body(
    text: str,
) -> tuple[dict[str, ConstraintParameter], str | None]:
    """Turn authored constraint body text into parameters plus expression.

    ``in name : Type`` becomes a typed definition parameter; ``in name = ref``
    becomes a usage binding stored in ``ConstraintParameter.value``. Any other
    statement is the boolean expression.
    """
    cleaned = _DOC_STRING.sub("", _remove_comments(text))
    cleaned = re.sub(r"\bdoc\b", "", cleaned)
    parameters: dict[str, ConstraintParameter] = {}
    expressions: list[str] = []
    for statement in _split_statements(cleaned):
        parameter_match = _IN_PARAMETER.match(statement)
        if parameter_match:
            name, type_name = parameter_match.groups()
            parameters[name] = ConstraintParameter(name=name, type_name=type_name)
            continue
        binding_match = _IN_BINDING.match(statement)
        if binding_match:
            name, reference = binding_match.groups()
            parameters[name] = ConstraintParameter(
                name=name, value=reference.strip()
            )
            continue
        expressions.append(statement)
    expression = " ".join(expressions).strip() or None
    return parameters, expression


def _body_text(dump: str) -> str:
    """Body between the first ``{`` and its matching ``}`` of a grammar dump."""
    masked = _mask_ignored(dump)
    opening = masked.find("{")
    if opening == -1:
        return ""
    closing = _matching_brace(masked, opening)
    return dump[opening + 1 : closing]


def constraint_usage(element) -> ConstraintUsage:
    """Repo ConstraintUsage from a parsed constraint usage element."""
    parameters, expression = parse_constraint_body(_body_text(element.grammar.dump()))
    bindings = {
        parameter.name: parameter.value
        for parameter in parameters.values()
        if parameter.value is not None
    }
    return ConstraintUsage(
        name=element.name,
        type_name=element.typed_by_name,
        bindings=bindings,
        expression=expression,
    )


def assert_constraint(element) -> tuple[str, bool]:
    """Target usage name and negation flag of an ``assert [not] name;``."""
    grammar = element.grammar
    for child in getattr(grammar, "children", []) or []:
        if type(child).__name__ != "OwnedReferenceSubsetting":
            continue
        name = child.dump().strip()
        if len(name) >= 2 and name[0] == name[-1] and name[0] in "'\"":
            name = name[1:-1]
        return name, bool(getattr(grammar, "isNegated", False))
    raise ValueError("assert constraint does not name a constraint usage")

