from __future__ import annotations

import xml.etree.ElementTree as ET

from pycps_sysmlv2 import SysMLParser
from pyssp_standard.ssd import SSD

from pyssp_sysml2.ssd import build_ssd
from tests.sysml_test_models import COMPOSITION_NAME, write_connected_triplet_architecture


def _connector_names(root: ET.Element) -> set[str]:
    return {
        elem.get("name")
        for elem in root.findall(".//{*}Connector")
        if elem.get("name")
    }


def _connection_tuples(root: ET.Element) -> set[tuple[str, str, str, str]]:
    connections = set()
    for elem in root.findall(".//{*}Connection"):
        connections.add(
            (
                elem.get("startElement"),
                elem.get("startConnector"),
                elem.get("endElement"),
                elem.get("endConnector"),
            )
        )
    return connections


def _connector_type_map(root: ET.Element) -> dict[tuple[str, str], str]:
    result = {}
    for component in root.findall(".//{*}Component"):
        cname = component.get("name")
        for connector in component.findall("./{*}Connectors/{*}Connector"):
            connector_name = connector.get("name")
            type_elem = next(iter(connector), None)
            if cname and connector_name and type_elem is not None:
                result[(cname, connector_name)] = type_elem.tag.split("}", 1)[-1]
    return result


def test_generate_ssd_from_small_snippet(tmp_path) -> None:
    architecture_dir = write_connected_triplet_architecture(tmp_path / "arch")
    output_path = tmp_path / "SystemStructure.ssd"
    system = SysMLParser(architecture_dir).parse().get_part(COMPOSITION_NAME)

    with SSD(output_path, mode="w") as ssd:
        build_ssd(ssd, system)

    tree = ET.parse(output_path)
    root = tree.getroot()

    components = root.findall(".//{*}Component")
    assert len(components) == 3

    connections = root.findall(".//{*}Connection")
    assert len(connections) == 4

    names = _connector_names(root)
    assert "gains[0]" in names
    assert "gains[1]" in names
    assert "gains[2]" in names

    conn_tuples = _connection_tuples(root)
    assert ("a", "cmd.pitch", "b", "cmdIn.pitch") in conn_tuples
    assert ("a", "cmd.mode", "b", "cmdIn.mode") in conn_tuples
    assert ("b", "pos.x", "c", "posIn.x") in conn_tuples
    assert ("b", "pos.y", "c", "posIn.y") in conn_tuples

    component_connectors = {}
    for component in root.findall(".//{*}Component"):
        cname = component.get("name")
        component_connectors[cname] = {
            (connector.get("name"), connector.get("kind"))
            for connector in component.findall(".//{*}Connector")
        }

    assert ("cmd.pitch", "output") in component_connectors["a"]
    assert ("cmdIn.pitch", "input") in component_connectors["b"]
    assert ("gains[0]", "parameter") in component_connectors["a"]

    type_map = _connector_type_map(root)
    assert type_map[("a", "cmd.mode")] == "Integer"
    assert type_map[("b", "pos.x")] == "Real"
    assert type_map[("a", "gains[0]")] == "Real"
