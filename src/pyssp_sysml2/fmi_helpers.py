"""Utility helpers for working with FMI artifacts derived from Modelica classes."""
from __future__ import annotations

from typing import Dict, Optional


def fmu_filename(modelica_class: str) -> str:
    """Return the FMU filename for a fully-qualified Modelica class."""
    return modelica_class.replace(".", "_") + ".fmu"


def fmu_resource_path(modelica_class: str) -> str:
    """Return the SSP resources relative path for an FMU."""
    return f"resources/{fmu_filename(modelica_class)}"


FMI_TYPE_MAP = {
    "real": "Real",
    "float": "Real",
    "float32": "Real",
    "float64": "Real",
    "double": "Real",
    "integer": "Integer",
    "int": "Integer",
    "int8": "Integer",
    "int32": "Integer",
    "uint8": "Integer",
    "uint32": "Integer",
    "boolean": "Boolean",
    "bool": "Boolean",
    "string": "String",
}

def map_fmi_type(type_name: Optional[str], default: str = "Real") -> str:
    """Return a canonical primitive name (Real/Integer/Boolean/String) for SysML types."""
    if not type_name:
        return default
    key = type_name.strip().lower()
    return FMI_TYPE_MAP.get(key, default)

def format_value(tag: str, literal):
    if literal is None:
        return ""
    if tag == "Real":
        return f"{float(literal):g}"
    if tag == "Integer":
        return str(int(literal))
    if tag == "Boolean":
        return "true" if bool(literal) else "false"
    if tag == "String":
        return str(literal)
    raise Exception("[format_value] Unknown tag")

def to_fmi_direction_definition(dir: str):
    if dir == "in":
        return "input"
    elif dir == "out":
        return "output"
    raise Exception("Direction conversion is unknown")