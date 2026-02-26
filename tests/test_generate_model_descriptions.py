from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from pyssp_sysml2.fmi import generate_model_descriptions

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "aircraft_subset"
REFERENCE_DIR = Path(__file__).parent / "reference"


def _variable_names(root: ET.Element) -> set[str]:
    return {
        elem.get("name")
        for elem in root.findall(".//ScalarVariable")
        if elem.get("name")
    }


def test_generate_model_descriptions_from_fixture() -> None:
    output_dir = REFERENCE_DIR / "model_descriptions"
    output_dir.mkdir(parents=True, exist_ok=True)

    written = generate_model_descriptions(
        architecture_path=FIXTURE_DIR,
        output_dir=output_dir,
        composition="AircraftComposition",
    )

    assert len(written) == 3

    autopilot_path = output_dir / "AutopilotModule" / "modelDescription.xml"
    assert autopilot_path in written

    root = ET.parse(autopilot_path).getroot()
    assert root.get("generationTool") == "pyssp_sysml2 tooling"

    names = _variable_names(root)
    assert "waypointX_km[0]" in names
    assert "waypointX_km[1]" in names
    assert "waypointX_km[2]" in names
