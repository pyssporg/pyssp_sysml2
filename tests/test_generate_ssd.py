from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from pycps_sysmlv2 import load_system
from pyssp_standard.ssd import SSD

from pyssp_sysml2.ssd import build_ssd

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "aircraft_subset"
REFERENCE_DIR = Path(__file__).parent / "reference"


def _connector_names(root: ET.Element) -> set[str]:
    return {
        elem.get("name")
        for elem in root.findall(".//{*}Connector")
        if elem.get("name")
    }


def test_generate_ssd_from_fixture() -> None:
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REFERENCE_DIR / "SystemStructure.ssd"
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
