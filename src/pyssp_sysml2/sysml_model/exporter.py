"""Conformant SysML v2 text export for the repo-owned architecture model.

The exporter emits text directly from the dataclasses in ``model.py`` (no
parser involvement), so the output format is a repo contract that cannot drift
with sysmlpy releases. Correctness of the emitted syntax is pinned by
round-trip tests that re-load exported text through the sysmlpy-backed loader.

Format (2-space indent, one blank line between definitions, trailing newline):

.. code-block:: text

    package Example {
      port def Signal {
        doc /* Air vehicle orientation. */
        attribute x : Real;
      }

      part def SystemComposition {
        part src : Source;
        connect src.outSig to dst.inSig;
      }
    }

Grouping follows the retired ``export_declared`` semantics: definitions are
grouped by ``source_file`` (default ``architecture.sysml````), file names are
sorted, and within a file requirements, ports, and parts each appear sorted by
name. Attributes, port usages, and part usages are sorted by name inside their
definition; connections keep insertion order.
"""

from __future__ import annotations

from typing import Protocol

from pyssp_sysml2.sysml_model.model import (
    Architecture,
    Attribute,
    Definition,
    PartDefinition,
    PortDefinition,
    PortUsage,
    RequirementDefinition,
)

DEFAULT_SOURCE_FILE = "architecture.sysml"

_DEFINITION_INDENT = "  "
_MEMBER_INDENT = "    "


def _format_value(value) -> str:
    """Render a Python literal as a SysML v2 literal expression."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return _quote(value)
    if isinstance(value, tuple):
        return "(" + ", ".join(_format_value(item) for item in value) + ")"
    if isinstance(value, (int, float)):
        return repr(value)
    return _quote(str(value))


def _quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _doc_line(doc: str | None, indent: str = _MEMBER_INDENT) -> list[str]:
    if not doc:
        return []
    return [f"{indent}doc /* {doc} */"]


def _attribute_lines(attribute: Attribute, indent: str = _MEMBER_INDENT) -> list[str]:
    lines = _doc_line(attribute.doc, indent)
    type_name = attribute.effective_type_name
    if attribute.value is not None:
        value = _format_value(attribute.value)
        lines.append(
            f"{indent}attribute {attribute.name} : {type_name} = {value};"
        )
    elif type_name:
        lines.append(f"{indent}attribute {attribute.name} : {type_name};")
    else:
        lines.append(f"{indent}attribute {attribute.name};")
    return lines


def _port_usage_lines(port: PortUsage, indent: str = _MEMBER_INDENT) -> list[str]:
    direction = f"{port.direction} " if port.direction else ""
    return _doc_line(port.doc, indent) + [
        f"{indent}{direction}port {port.name} : {port.type_name};"
    ]


def _part_definition_lines(part_def: PartDefinition) -> list[str]:
    lines = [f"{_DEFINITION_INDENT}part def {part_def.name} {{"]
    if part_def.doc:
        lines.extend(_doc_line(part_def.doc, _MEMBER_INDENT))

    def member_lines():
        for attribute in sorted(part_def.attributes.values(), key=lambda a: a.name):
            yield from _attribute_lines(attribute)
        for port in sorted(part_def.ports.values(), key=lambda p: p.name):
            yield from _port_usage_lines(port)
        for part in sorted(part_def.parts.values(), key=lambda p: p.name):
            yield from _doc_line(part.doc)
            yield f"{_MEMBER_INDENT}part {part.name} : {part.type_name};"
        for connection in part_def.connections.values():  # insertion order
            yield from _doc_line(connection.doc)
            yield (
                f"{_MEMBER_INDENT}connect {connection.source_part}.{connection.source_port}"
                f" to {connection.destination_part}.{connection.destination_port};"
            )

    lines.extend(member_lines())
    lines.append(f"{_DEFINITION_INDENT}}}")
    return lines


def _port_definition_lines(port_def: PortDefinition) -> list[str]:
    lines = [f"{_DEFINITION_INDENT}port def {port_def.name} {{"]
    if port_def.doc:
        lines.extend(_doc_line(port_def.doc, _MEMBER_INDENT))
    for attribute in sorted(port_def.attributes.values(), key=lambda a: a.name):
        lines.extend(_attribute_lines(attribute))
    lines.append(f"{_DEFINITION_INDENT}}}")
    return lines


def _requirement_definition_lines(
    requirement_def: RequirementDefinition,
) -> list[str]:
    lines = [f"{_DEFINITION_INDENT}requirement def {requirement_def.name} {{"]
    if requirement_def.text:
        lines.extend(_doc_line(requirement_def.text, _MEMBER_INDENT))
    lines.append(f"{_DEFINITION_INDENT}}}")
    return lines


def _definition_lines(definition: Definition) -> list[str]:
    if isinstance(definition, PartDefinition):
        return _part_definition_lines(definition)
    if isinstance(definition, PortDefinition):
        return _port_definition_lines(definition)
    if isinstance(definition, RequirementDefinition):
        return _requirement_definition_lines(definition)
    raise TypeError(f"Unsupported definition type for export: {type(definition)!r}")


def export_declared(architecture: Architecture) -> dict[str, str]:
    """Emit one SysML v2 text per source file, keyed by bare file name."""
    groups: dict[str, list[Definition]] = {}

    def collect(definitions) -> None:
        for definition in sorted(definitions, key=lambda d: d.name):
            file_name = definition.source_file or DEFAULT_SOURCE_FILE
            groups.setdefault(file_name, []).append(definition)

    # Collect in requirements → ports → parts order so each file's layout
    # follows the retired exporter's layout.
    collect(architecture.requirement_definitions.values())
    collect(architecture.port_definitions.values())
    collect(architecture.part_definitions.values())

    files: dict[str, str] = {}
    for file_name in sorted(groups):
        lines = [f"package {architecture.package_name} {{"]
        for index, definition in enumerate(groups[file_name]):
            if index:
                lines.append("")
            lines.extend(_definition_lines(definition))
        lines.append("}")
        files[file_name] = "\n".join(lines) + "\n"
    return files
