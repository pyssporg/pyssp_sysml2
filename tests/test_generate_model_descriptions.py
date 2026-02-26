from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from pyssp_sysml2.generate_model_descriptions import generate_model_descriptions

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "aircraft_subset"


def _variable_names(root: ET.Element) -> set[str]:
    return {
        elem.get("name")
        for elem in root.findall(".//ScalarVariable")
        if elem.get("name")
    }


def test_generate_model_descriptions_from_fixture(tmp_path: Path) -> None:
    output_dir = tmp_path / "model_descriptions"

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
