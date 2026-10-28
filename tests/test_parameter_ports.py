from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from pyssp_standard import SSD

from pyssp_sysml2.fmi import generate_model_descriptions
from pyssp_sysml2.parameters import (
    parameter_declarations,
    parameter_interface,
    validate_marker_definitions,
)
from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.sysml_model import load
from tests.testhelpers import COMPOSITION_NAME, write_model


def _model(
    *,
    port: str = "in port parameters : Params;",
    markers: str = (
        "port def ParameterInterface;\n"
        "  attribute def ParameterSet;"
    ),
    interface_decl: str = "port def Params :> ParameterInterface",
    interface_members: str = (
        "attribute gain : Real = 2.0;\n"
        "    attribute count : Integer;\n"
        "    attribute xs : Real[2];"
    ),
) -> str:
    return f"""
    package Ports {{
      {markers}

      {interface_decl} {{
        {interface_members}
      }}

      attribute def Nom :> ParameterSet {{
        attribute gain_value = 3.0;
        attribute n = 7;
        attribute xs_value = (1.0, 2.0);
      }}

      part def Comp {{
        {port}
      }}

      part def {COMPOSITION_NAME} {{
        part comp : Comp;
        attribute nominal : Nom;
        bind comp.parameters.gain = nominal.gain_value;
        bind comp.parameters.count = nominal.n;
        bind comp.parameters.xs = nominal.xs_value;
      }}
    }}
    """


def _load(tmp_path: Path, text: str):
    architecture_dir = tmp_path / "arch"
    write_model(architecture_dir / "model.sysml", text)
    return architecture_dir, load(architecture_dir)


@pytest.mark.parametrize(
    "port",
    ["in port parameters : Params;", "port parameters : Params;"],
)
def test_parameter_interface_is_a_port(tmp_path, port: str) -> None:
    """The parameter port is an input (or undirected) port typed by a marked port def."""
    _, architecture = _load(tmp_path, _model(port=port))
    part_def = architecture.get_part_def("Comp")

    interface = parameter_interface(architecture, part_def)

    assert interface is not None
    assert interface.specializes == ("ParameterInterface",)
    assert list(interface.attributes) == ["gain", "count", "xs"]
    assert part_def.ports["parameters"].direction in (None, "in")
    assert part_def.attributes == {}
    assert [attribute.name for attribute in parameter_declarations(architecture, part_def)] == [
        "gain",
        "count",
        "xs",
    ]


def test_out_direction_is_rejected(tmp_path) -> None:
    """A parameter port is not an output signal."""
    _, architecture = _load(
        tmp_path, _model(port="out port parameters : Params;")
    )

    with pytest.raises(ValueError, match="undirected or 'in'"):
        parameter_interface(architecture, architecture.get_part_def("Comp"))


def test_attribute_bag_is_rejected(tmp_path) -> None:
    """The retired attribute carrier fails with a migration hint."""
    _, architecture = _load(
        tmp_path, _model(port="attribute parameters : Params;")
    )

    with pytest.raises(ValueError, match="attribute bag"):
        parameter_interface(architecture, architecture.get_part_def("Comp"))


def test_attribute_marker_is_rejected(tmp_path) -> None:
    """ParameterInterface must be a port def, not an attribute def."""
    _, architecture = _load(
        tmp_path,
        _model(
            markers=(
                "attribute def ParameterInterface;\n"
                "  attribute def ParameterSet;"
            ),
        ),
    )

    with pytest.raises(ValueError, match="defined as an attribute def"):
        validate_marker_definitions(architecture)


def test_flat_connector_marker_is_rejected(tmp_path) -> None:
    """A parameter interface cannot flatten to the port name."""
    _, architecture = _load(
        tmp_path,
        _model(
            interface_members=(
                "attribute pyssp_flat_connector : Boolean = true;\n"
                "    attribute gain : Real;"
            ),
        ),
    )

    with pytest.raises(ValueError, match="cannot declare"):
        parameter_interface(architecture, architecture.get_part_def("Comp"))


def test_parameter_port_cannot_be_connected(tmp_path) -> None:
    """Parameter ports are bound, not wired with 'connect'."""
    model = f"""
    package Ports {{
      port def ParameterInterface;
      attribute def ParameterSet;

      port def Params :> ParameterInterface {{
        attribute gain : Real;
      }}

      part def Comp {{
        in port parameters : Params;
      }}

      part def {COMPOSITION_NAME} {{
        part left : Comp;
        part right : Comp;
        connect left.parameters to right.parameters;
      }}
    }}
    """
    architecture_dir, _ = _load(tmp_path, model)

    with pytest.raises(ValueError, match="cannot be connected"):
        generate_ssd(
            architecture_dir, tmp_path / "SystemStructure.ssd", COMPOSITION_NAME
        )


def test_fmi_parameters_are_flat_with_parameter_causality(tmp_path) -> None:
    """Names do not include the port; causality stays 'parameter'."""
    architecture_dir, _ = _load(tmp_path, _model())

    [path] = generate_model_descriptions(
        architecture_dir, tmp_path / "model_descriptions", COMPOSITION_NAME
    )
    root = ET.parse(path).getroot()
    variables = root.findall(".//ScalarVariable")

    assert {variable.get("name") for variable in variables} == {
        "gain",
        "count",
        "xs[0]",
        "xs[1]",
    }
    assert {variable.get("causality") for variable in variables} == {"parameter"}
    starts = {
        variable.get("name"): next(iter(variable)).get("start")
        for variable in variables
    }
    assert starts["gain"] == "2"


def test_ssd_connectors_are_flat_parameter_connectors(tmp_path) -> None:
    """The parameter port does not leak into signal connectors."""
    architecture_dir, _ = _load(tmp_path, _model())
    output_path = tmp_path / "SystemStructure.ssd"

    generate_ssd(architecture_dir, output_path, COMPOSITION_NAME)

    with SSD(output_path, mode="r") as ssd:
        component = ssd.system.elements[0]
        assert sorted(
            (connector.name, connector.kind, connector.type_name)
            for connector in component.connectors
        ) == [
            ("count", "parameter", "Integer"),
            ("gain", "parameter", "Real"),
            ("xs[0]", "parameter", "Real"),
            ("xs[1]", "parameter", "Real"),
        ]
