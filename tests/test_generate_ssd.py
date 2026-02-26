from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from pycps_sysmlv2 import load_system
from pyssp_standard.ssd import SSD

from pyssp_sysml2.generate_ssd import build_ssd

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "aircraft_subset"


def _connector_names(root: ET.Element) -> set[str]:
    return {
        elem.get("name")
        for elem in root.findall(".//{*}Connector")
        if elem.get("name")
    }


def test_generate_ssd_from_fixture(tmp_path: Path) -> None:
    output_path = tmp_path / "SystemStructure.ssd"
    system = load_system(FIXTURE_DIR, "AircraftComposition")

    with SSD(output_path, mode="w") as ssd:
        build_ssd(ssd, system)

    tree = ET.parse(output_path)
    root = tree.getroot()

    components = root.findall(".//{*}Component")
    assert len(components) == 3

    connections = root.findall(".//{*}Connection")
    assert len(connections) == 15

    names = _connector_names(root)
    assert "waypointX_km[0]" in names
    assert "waypointX_km[1]" in names
    assert "waypointX_km[2]" in names
