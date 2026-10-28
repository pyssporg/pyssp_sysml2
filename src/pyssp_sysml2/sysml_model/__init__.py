"""SysML v2 model adapter for pyssp_sysml2.

Anti-corruption layer over the external `sysmlpy` parser:

- ``model.py``    — the repo-owned dataclasses every generator works against.
- ``loader.py``   — the ONLY module that imports ``sysmlpy``; builds the
  repo-owned model from ``.sysml`` files.
- ``exporter.py`` — emits conformant SysML v2 text from the repo-owned model
  (no parser involvement, so the output format is a repo contract).

If sysmlpy's API changes, only ``loader.py`` needs fixes.
"""

from pyssp_sysml2.sysml_model.model import (
    Architecture,
    Attribute,
    AttributeDefinition,
    Binding,
    Connection,
    Definition,
    PartDefinition,
    PartUsage,
    PortDefinition,
    PortUsage,
    RequirementDefinition,
    VariantBody,
    VariantMember,
    endpoint_text,
)

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
    "VariantBody",
    "VariantMember",
    "endpoint_text",
    "load",
]


def load(path) -> Architecture:
    """Load a ``.sysml`` file or directory into an :class:`Architecture`.

    Implemented in :mod:`pyssp_sysml2.sysml_model.loader`.
    """
    from pyssp_sysml2.sysml_model.loader import load as _load

    return _load(path)
