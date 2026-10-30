"""File orchestration: builds the repo-owned model from ``.sysml`` files.

This module walks a load target, asks :mod:`pyssp_sysml2.model.parser` for one
file's packages and :mod:`pyssp_sysml2.model.variation` for that file's
variation facts, merges every package into one
:class:`~pyssp_sysml2.model.model.Architecture`, and builds the repo-owned
dataclasses from the parsed elements.

The parser boundary is exactly one module: only
:mod:`pyssp_sysml2.model.parser` imports ``sysmlpy`` and reads raw ANTLR trees,
and only :mod:`pyssp_sysml2.model.variation` walks the tree for variation
points; every other module works against the repo-owned model, never against
sysmlpy objects. Loading stays non-validating, so unresolved references simply
surface as ``resolve_part``/``resolve_port`` returning ``None`` in consumers.
"""

from __future__ import annotations

from pathlib import Path

from pyssp_sysml2.model.model import (
    Architecture,
    Attribute,
    AttributeDefinition,
    Binding,
    Connection,
    ConstraintDefinition,
    ConstraintUsage,
    PartDefinition,
    PartUsage,
    PortDefinition,
    PortUsage,
    RequirementDefinition,
    endpoint_text,
)
from pyssp_sysml2.model.parser import (
    UUID_PATTERN,
    assert_constraint,
    binding_endpoints,
    connection_endpoint,
    connection_endpoints,
    constraint_definitions_from_source,
    constraint_usage,
    is_definition_variation,
    multiplicity,
    normalize_value,
    parse_constraint_body,
    port_direction,
    specializes,
    parse_packages,
)
from pyssp_sysml2.model.variation import VariationFacts, variation_facts

__all__ = ["load"]


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
    packages, variation, source = _parse_file(file)
    architecture = Architecture(package_name=packages[0].name)
    _merge_packages(architecture, packages, file, variation, source)
    return architecture


def _merge_file(architecture: Architecture, file: Path) -> None:
    """Merge one more file into ``architecture`` (package names must match)."""
    packages, variation, source = _parse_file(file)
    name = packages[0].name
    if name != architecture.package_name:
        raise ValueError(
            f"Mismatched package names: {architecture.package_name} vs {name} in {file}"
        )
    _merge_packages(architecture, packages, file, variation, source)


def _parse_file(file: Path) -> tuple[list, VariationFacts, str]:
    """Parse one file: its package(s), variation facts, and source text.

    The source text is read once here: ``parse_packages`` takes the path, the
    raw-tree walk takes the text, and constraint-definition bodies are scanned
    from the same text, so capture adds no second read.
    """
    source = file.read_text(encoding="utf-8")
    return parse_packages(file), variation_facts(source), source


def _merge_packages(
    architecture: Architecture,
    packages: list,
    file: Path,
    variation: VariationFacts,
    source: str,
) -> None:
    """Add every definition of one file's package(s) to the architecture.

    Top-level usages and other non-definition children are skipped silently
    (legacy parity). Definitions are added parts first, then ports, then
    attribute definitions, then requirements, then constraint definitions.
    """
    constraint_bodies = constraint_definitions_from_source(source)
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
        for element in package.constraints:
            if element.is_definition:
                constraint_def = _constraint_definition(
                    element, file, constraint_bodies
                )
                _add_definition(
                    architecture, architecture.add_constraint_def, constraint_def, file
                )


def _add_definition(architecture: Architecture, add, definition, file: Path) -> None:
    """Add a definition, re-raising duplicates with file context (legacy parity)."""
    try:
        add(definition)
    except ValueError:
        kind = type(definition).__name__.removesuffix("Definition").lower()
        raise ValueError(f"Duplicate {kind} definition for {definition.name} in {file}") from None


# -- definition builders ----------------------------------------------------


def _part_definition(element, file: Path, variation: VariationFacts) -> PartDefinition:
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
        specializes=specializes(element),
        is_variation=is_definition_variation(element),
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
            direction=port_direction(port),
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
    _attach_constraints(part_def, element, file)
    return part_def


def _attach_constraints(
    part_def: PartDefinition, element, file: Path
) -> None:
    """Append constraint usages and apply their ``assert`` statements.

    A constraint definition nested in a part def is not a usage and is skipped;
    ``assert`` statements are resolved to the usage they name after every usage
    has been collected.
    """
    asserts: list[tuple[str, bool]] = []
    for child in element.constraints:
        if getattr(child, "is_definition", False):
            continue
        if type(child.grammar).__name__ == "AssertConstraintUsage":
            asserts.append(assert_constraint(child))
            continue
        usage = constraint_usage(child)
        usage.source_file = file.name
        part_def.constraints.append(usage)
    for name, negated in asserts:
        for usage in part_def.constraints:
            if usage.name == name:
                usage.asserted = True
                usage.negated = negated
                break
        else:
            raise ValueError(
                f"assert names unknown constraint usage '{name}' in "
                f"'{part_def.name}' ({file})"
            )


def _port_definition(element, file: Path) -> PortDefinition:
    """Repo PortDefinition from a sysmlpy port definition."""
    port_def = PortDefinition(
        name=element.name,
        doc=element.doc,
        source_file=file.name,
        specializes=specializes(element),
    )
    for attribute in element.attributes:
        port_def.attributes[attribute.name] = _attribute(attribute)
    return port_def


def _attribute_definition(
    element, file: Path, variation: VariationFacts
) -> AttributeDefinition:
    """Repo AttributeDefinition from a sysmlpy attribute definition."""
    attribute_def = AttributeDefinition(
        name=element.name,
        doc=element.doc,
        source_file=file.name,
        specializes=specializes(element),
        is_variation=element.name in variation.attribute_points,
        variants=list(variation.attribute_variants.get(element.name, ())),
    )
    for attribute in element.attributes:
        attribute_def.attributes[attribute.name] = _attribute(attribute)
    return attribute_def


def _requirement_definition(element, file: Path) -> RequirementDefinition:
    """Repo RequirementDefinition; the doc comment is the requirement text."""
    return RequirementDefinition(name=element.name, text=element.doc, source_file=file.name)


def _constraint_definition(
    element, file: Path, bodies: dict[str, str]
) -> ConstraintDefinition:
    """Repo ConstraintDefinition from the source-scanned authored body.

    ``sysmlpy`` garbles the expression of a constraint definition in its
    grammar dump, so the body is read from the authored source text instead.
    """
    parameters, expression = parse_constraint_body(bodies.get(element.name, ""))
    return ConstraintDefinition(
        name=element.name,
        doc=element.doc,
        source_file=file.name,
        parameters=parameters,
        expression=expression,
    )


def _connection(connect, file: Path) -> Connection:
    """Repo Connection from a sysmlpy connect statement.

    Only binary connects are supported. An end is either part-qualified
    (``connect a.p to b.q;``) or a bare port name that refers to a port of the
    enclosing part def, i.e. the system boundary (``connect gain.y to y;``).
    A parsed name of ``None`` or a UUID means sysmlpy generated it for an
    unnamed connect, so the legacy endpoint-derived name is rebuilt instead.
    """
    ends = connection_endpoints(connect)
    if len(ends) != 2:
        raise ValueError(
            f"Only binary connections are supported ('connect a.p to b.q;'), "
            f"got {len(ends)} ends in {file}"
        )
    source, destination = ends
    source_part, source_port = connection_endpoint(source, file)
    destination_part, destination_port = connection_endpoint(destination, file)
    name = connect.name
    if name is None or UUID_PATTERN.match(name):
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


def _binding(bind, file: Path) -> Binding:
    """Repo Binding from a sysmlpy ``bind a.x = b.y;`` statement.

    Both endpoints keep their full feature chain. Unnamed bindings receive a
    UUID name from sysmlpy; those are normalized back to ``None``.
    """
    ends = binding_endpoints(bind)
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
    if name is None or UUID_PATTERN.match(name):
        name = None
    return Binding(source=tuple(source), target=tuple(target), name=name)


# -- attribute usages -------------------------------------------------------


def _attribute(element) -> Attribute:
    """Repo Attribute from a sysmlpy attribute usage."""
    return Attribute(
        name=element.name,
        type_name=element.typed_by_name,
        value=normalize_value(element),
        multiplicity=multiplicity(element),
    )
