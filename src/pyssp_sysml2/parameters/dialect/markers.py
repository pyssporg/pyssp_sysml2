"""Parameter marker vocabulary: marker names and role predicates."""

from __future__ import annotations

from pyssp_sysml2.model import (
    Architecture,
    AttributeDefinition,
    PortDefinition,
)


PARAMETERS_PORT_NAME = "parameters"

# Marker definitions the dialect relies on. Models declare them as ordinary
# (empty) port or attribute definitions; the last qualified-name segment is
# matched so ``Pyssp::ParameterSet`` works as well as the bare name.
PARAMETER_INTERFACE_MARKER = "ParameterInterface"
PARAMETER_SET_MARKER = "ParameterSet"


# -- role predicates --------------------------------------------------------


def _specializes_marker(
    definition: AttributeDefinition | PortDefinition | None, marker: str
) -> bool:
    if definition is None:
        return False
    return any(
        name.split("::")[-1] == marker for name in definition.specializes
    )


def is_parameter_interface(definition: PortDefinition | None) -> bool:
    """True when ``definition`` is a port def marked ``:> ParameterInterface``."""
    return _specializes_marker(definition, PARAMETER_INTERFACE_MARKER)


def is_parameter_set(definition: AttributeDefinition | None) -> bool:
    """True when ``definition`` is marked ``:> ParameterSet``."""
    return _specializes_marker(definition, PARAMETER_SET_MARKER)


def parameter_set_resource(prefix: str, set_name: str) -> str:
    """Archive-relative path of one parameter set inside an SSP."""
    prefix = prefix.strip().strip("/")
    return f"{prefix}/{set_name}.ssv" if prefix else f"{set_name}.ssv"


def validate_marker_definitions(architecture: Architecture) -> None:
    """Require the marker defs used by ``:>`` to exist with the right kind."""
    interface_users = [
        definition.name
        for definition in architecture.port_definitions.values()
        if _specializes_marker(definition, PARAMETER_INTERFACE_MARKER)
    ]
    set_users = [
        definition.name
        for definition in architecture.attribute_definitions.values()
        if _specializes_marker(definition, PARAMETER_SET_MARKER)
    ]
    attribute_interfaces = [
        definition.name
        for definition in architecture.attribute_definitions.values()
        if _specializes_marker(definition, PARAMETER_INTERFACE_MARKER)
    ]
    port_sets = [
        definition.name
        for definition in architecture.port_definitions.values()
        if _specializes_marker(definition, PARAMETER_SET_MARKER)
    ]

    if attribute_interfaces:
        raise ValueError(
            "Parameter interfaces must be port defs; these attribute defs "
            f"specialize '{PARAMETER_INTERFACE_MARKER}': "
            f"{', '.join(sorted(attribute_interfaces))}. Use "
            f"'port def <name> :> {PARAMETER_INTERFACE_MARKER} {{ ... }}'."
        )
    if port_sets:
        raise ValueError(
            "Parameter sets must be attribute defs; these port defs specialize "
            f"'{PARAMETER_SET_MARKER}': {', '.join(sorted(port_sets))}. Use "
            f"'attribute def <name> :> {PARAMETER_SET_MARKER} {{ ... }}'."
        )

    if (
        interface_users
        and PARAMETER_INTERFACE_MARKER in architecture.attribute_definitions
        and PARAMETER_INTERFACE_MARKER not in architecture.port_definitions
    ):
        raise ValueError(
            f"'{PARAMETER_INTERFACE_MARKER}' is defined as an attribute def, but "
            "parameter interfaces are port defs. Replace "
            f"'attribute def {PARAMETER_INTERFACE_MARKER};' with "
            f"'port def {PARAMETER_INTERFACE_MARKER};'."
        )
    if (
        set_users
        and PARAMETER_SET_MARKER in architecture.port_definitions
        and PARAMETER_SET_MARKER not in architecture.attribute_definitions
    ):
        raise ValueError(
            f"'{PARAMETER_SET_MARKER}' is defined as a port def, but parameter "
            "sets are attribute defs. Replace "
            f"'port def {PARAMETER_SET_MARKER};' with "
            f"'attribute def {PARAMETER_SET_MARKER};'."
        )

    missing: list[tuple[str, str]] = []
    if (
        interface_users
        and PARAMETER_INTERFACE_MARKER not in architecture.port_definitions
    ):
        missing.append((PARAMETER_INTERFACE_MARKER, "port def"))
    if (
        set_users
        and PARAMETER_SET_MARKER not in architecture.attribute_definitions
    ):
        missing.append((PARAMETER_SET_MARKER, "attribute def"))
    if missing:
        definitions = ", ".join(
            f"{kind} {marker};" for marker, kind in missing
        )
        raise ValueError(
            "Parameter dialect uses missing marker definition(s) "
            f"{', '.join(marker for marker, _ in missing)}. Add "
            f"{definitions} to the package."
        )
