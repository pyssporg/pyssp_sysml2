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
