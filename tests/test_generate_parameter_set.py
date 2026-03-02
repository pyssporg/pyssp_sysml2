from __future__ import annotations

import xml.etree.ElementTree as ET

from pyssp_sysml2.ssv import generate_parameter_set
from tests.sysml_test_models import COMPOSITION_NAME, write_connected_triplet_architecture


def _parameter_names(root: ET.Element) -> set[str]:
    return {
        elem.get("name")
        for elem in root.findall(".//{*}Parameter")
        if elem.get("name")
    }


def test_generate_parameter_set_uses_zero_based_indexing(tmp_path) -> None:
    architecture_dir = write_connected_triplet_architecture(tmp_path / "arch")
    output_path = tmp_path / "parameters.ssv"
    written = generate_parameter_set(architecture_dir, output_path, COMPOSITION_NAME)

    assert written == output_path
    assert output_path.exists()

    root = ET.parse(output_path).getroot()
    names = _parameter_names(root)

    assert "a.gains[0]" in names
    assert "a.gains[1]" in names
    assert "a.gains[2]" in names
    assert "a.gains[3]" not in names
