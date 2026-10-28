"""Parameter interface resolution, declaration items, and multiplicity."""

from __future__ import annotations

from dataclasses import dataclass

from pyssp_sysml2.core.control import FLAT_CONNECTOR_ATTR, is_control_attribute
from pyssp_sysml2.model import (
    Architecture,
    Attribute,
    PartDefinition,
    PortDefinition,
    PortUsage,
)
from pyssp_sysml2.parameters.dialect.markers import (
    PARAMETER_INTERFACE_MARKER,
    PARAMETERS_PORT_NAME,
    is_parameter_interface,
)


# -- interface and declaration resolution -----------------------------------


def parameter_port(
    architecture: Architecture, part_def: PartDefinition
) -> PortUsage | None:
    """The ``parameters`` port of a part def, when its type is a port def.

    An attribute bag is the retired carrier and is rejected with a migration
    hint, so the two carriers never coexist silently.
    """
    if PARAMETERS_PORT_NAME in part_def.attributes:
        raise ValueError(
            f"{part_def.name}.{PARAMETERS_PORT_NAME} is an attribute bag; "
            "parameter interfaces are port defs. Use "
            f"'in port {PARAMETERS_PORT_NAME} : <PortDef>;' instead."
        )
    port_usage = part_def.ports.get(PARAMETERS_PORT_NAME)
    if port_usage is None:
        return None
    if architecture.resolve_port(port_usage) is None:
        raise ValueError(
            f"Unresolved port definition for "
            f"{part_def.name}.{PARAMETERS_PORT_NAME}"
        )
    return port_usage


def parameter_interface(
    architecture: Architecture, part_def: PartDefinition
) -> PortDefinition | None:
    """Resolve and validate the parameter interface of a part def.

    ``None`` means the part declares no parameters. A ``parameters`` port
    typed by an unmarked port def is an error: the dialect requires the marker
    so role confusion is caught early. Parameter ports are
    undirected or ``in``; other directions are rejected because the SSP/FMI
    role is ``parameter``, not an input/output signal.
    """
    port_usage = parameter_port(architecture, part_def)
    if port_usage is None:
        return None
    definition = architecture.resolve_port(port_usage)
    assert definition is not None  # parameter_port already resolved it
    if not is_parameter_interface(definition):
        raise ValueError(
            f"Parameter port {part_def.name}.{PARAMETERS_PORT_NAME} is typed by "
            f"'{definition.name}', which is not marked ':> {PARAMETER_INTERFACE_MARKER}'"
        )
    if port_usage.direction not in (None, "in"):
        raise ValueError(
            f"Parameter port {part_def.name}.{PARAMETERS_PORT_NAME} must be "
            f"undirected or 'in', got '{port_usage.direction}'"
        )
    if FLAT_CONNECTOR_ATTR in definition.attributes:
        raise ValueError(
            f"Parameter interface '{definition.name}' cannot declare "
            f"'{FLAT_CONNECTOR_ATTR}'; parameter members are emitted by name"
        )
    return definition


def parameter_declarations(
    architecture: Architecture, part_def: PartDefinition
) -> list[Attribute]:
    """Ordered parameter declarations from a component's parameter interface.

    Parameters are only declared through ``in port parameters : <Interface>``.
    Flat parameter attributes were retired; callers validate the architecture
    with :func:`validate_parameter_dialect` before generating artifacts.
    """
    interface = parameter_interface(architecture, part_def)
    if interface is None:
        return []
    return [
        attribute
        for name, attribute in interface.attributes.items()
        if not is_control_attribute(name)
    ]



# -- parameter items --------------------------------------------------------


@dataclass(frozen=True)
class ParameterItem:
    """One SSP-level parameter after expanding a declared multiplicity."""

    name: str
    type_name: str
    value: object = None


def parameter_items(attribute: Attribute) -> list[ParameterItem]:
    """Expand an attribute's multiplicity/list value into SSP parameter items.

    Interfaces use the declared multiplicity (``Real[3]``) even without a
    value; legacy tuple values expand element-wise. The value is the declared
    default when present, otherwise ``None``.
    """
    type_name = attribute.primitive_type_str()
    if attribute.multiplicity:
        count = fixed_count(attribute.multiplicity, attribute.name)
        value = attribute.value
        if value is None:
            values: tuple = (None,) * count
        elif not isinstance(value, tuple):
            raise ValueError(
                f"Parameter '{attribute.name}' must provide {count} values for "
                f"[{attribute.multiplicity}], got a scalar"
            )
        elif len(value) != count:
            raise ValueError(
                f"Parameter '{attribute.name}' provides {len(value)} values but "
                f"declares [{attribute.multiplicity}]"
            )
        else:
            values = value
        return [
            ParameterItem(
                name=f"{attribute.name}[{index}]",
                type_name=type_name,
                value=values[index],
            )
            for index in range(count)
        ]

    if attribute.is_list:
        return [
            ParameterItem(
                name=f"{attribute.name}[{index}]",
                type_name=type_name,
                value=value,
            )
            for index, value in enumerate(attribute.value)
        ]

    return [
        ParameterItem(
            name=attribute.name,
            type_name=type_name,
            value=attribute.value,
        )
    ]


def coerce_parameter_value(type_name: str, value: object) -> object:
    """Coerce an SSV literal to the Python type used in SysML attributes."""
    if value is None:
        return None
    if type_name == "Real":
        return float(value)
    if type_name == "Integer":
        return int(value)
    if type_name == "Boolean":
        return str(value).lower() == "true"
    return str(value)



# -- multiplicity -----------------------------------------------------------


def fixed_count(multiplicity: str, name: str) -> int:
    """Number of elements for a fixed multiplicity, or error when variable."""
    if multiplicity == "*" or multiplicity.endswith("..*"):
        raise ValueError(
            f"Parameter '{name}' has unbounded multiplicity '[{multiplicity}]'; "
            "SSP parameters need a fixed length"
        )
    if ".." in multiplicity:
        lower, upper = multiplicity.split("..", 1)
        if lower != upper:
            raise ValueError(
                f"Parameter '{name}' has variable multiplicity '[{multiplicity}]'; "
                "SSP parameters need a fixed length"
            )
        multiplicity = lower
    try:
        return int(multiplicity)
    except ValueError:
        raise ValueError(
            f"Parameter '{name}' has unsupported multiplicity '[{multiplicity}]'"
        ) from None
