from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from pyssp_sysml2.ssv import generate_parameter_set

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "aircraft_subset"
REFERENCE_DIR = Path(__file__).parent  / "reference"


def _parameter_names(root: ET.Element) -> set[str]:
    return {
        elem.get("name")
        for elem in root.findall(".//{*}Parameter")
        if elem.get("name")
    }


def test_generate_parameter_set_uses_zero_based_indexing() -> None:
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REFERENCE_DIR / "parameters.ssv"
    written = generate_parameter_set(FIXTURE_DIR, output_path, "AircraftComposition")

    assert written == output_path
    assert output_path.exists()

    root = ET.parse(output_path).getroot()
    names = _parameter_names(root)

    assert "autopilot.waypointX_km[0]" in names
    assert "autopilot.waypointX_km[1]" in names
    assert "autopilot.waypointX_km[2]" in names
    assert "autopilot.waypointX_km[3]" not in names
