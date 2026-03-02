from __future__ import annotations

import xml.etree.ElementTree as ET

from pyssp_sysml2.fmi import generate_model_descriptions
from tests.sysml_test_models import COMPOSITION_NAME, write_connected_triplet_architecture


def _variable_names(root: ET.Element) -> set[str]:
    return {
        elem.get("name")
        for elem in root.findall(".//ScalarVariable")
        if elem.get("name")
    }


def test_generate_model_descriptions_from_small_snippet(tmp_path) -> None:
    architecture_dir = write_connected_triplet_architecture(tmp_path / "arch")
    output_dir = tmp_path / "model_descriptions"

    written = generate_model_descriptions(
        architecture_path=architecture_dir,
        output_dir=output_dir,
        composition=COMPOSITION_NAME,
    )

    assert len(written) == 3

    a_path = output_dir / "A" / "modelDescription.xml"
    assert a_path in written

    root = ET.parse(a_path).getroot()
    assert root.get("generationTool") == "pyssp_sysml2 tooling"

    names = _variable_names(root)
    assert "gains[0]" in names
    assert "gains[1]" in names
    assert "gains[2]" in names
