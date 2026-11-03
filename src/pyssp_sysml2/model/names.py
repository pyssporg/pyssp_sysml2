"""SysML v2 declared-name handling shared by the adapter and the exporter.

A SysML name is either a simple identifier (``X``, ``pipeA``) or a
single-quoted name (``'X[1]'``, ``'pipeA.L'``). The repo-owned model stores the
declared name without its quotes, so an SSD/FMI/SSV name can carry characters a
SysML identifier cannot (dots, brackets, spaces, leading digits). The exporter
re-quotes a name that is not a simple identifier so the emitted text stays
valid SysML.

Quoted names escape ``\\`` and ``'`` with a backslash; :func:`unquote_name` and
:func:`quote_name` are inverse for those escapes.
"""

from __future__ import annotations

import re

__all__ = ["RESERVED_IDENTIFIERS", "quote_name", "unquote_name"]

_SIMPLE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_QUOTED_ESCAPE = re.compile(r"\\([\\'])")

#: SysML keywords that cannot stand as a bare feature or definition name.
#: A name in this set is emitted quoted, so a quoted authored name round-trips.
RESERVED_IDENTIFIERS = frozenset(
    {
        "action",
        "alias",
        "allocate",
        "analysis",
        "attribute",
        "bind",
        "calc",
        "comment",
        "concern",
        "connection",
        "constraint",
        "def",
        "dependency",
        "doc",
        "expose",
        "flow",
        "import",
        "interface",
        "item",
        "metadata",
        "occurrence",
        "package",
        "part",
        "perform",
        "port",
        "ref",
        "rendering",
        "requirement",
        "satisfy",
        "stakeholder",
        "state",
        "typed",
        "verification",
        "view",
        "viewpoint",
    }
)


def unquote_name(text: str) -> str:
    """Declared name of a parsed name token: strip single quotes and decode escapes."""
    if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
        return _QUOTED_ESCAPE.sub(lambda match: match.group(1), text[1:-1])
    return text


def quote_name(text: str) -> str:
    """SysML name token for a declared name: bare when simple, quoted otherwise."""
    if _SIMPLE_NAME.match(text) and text not in RESERVED_IDENTIFIERS:
        return text
    escaped = text.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"
