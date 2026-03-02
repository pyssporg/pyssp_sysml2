from __future__ import annotations

import xml.etree.ElementTree as ET

from pyssp_sysml2.ssv import generate_parameter_set
from tests.sysml_test_models import COMPOSITION_NAME, write_ssv_type_coverage_architecture


def _parameter_names(root: ET.Element) -> set[str]:
    return {
        elem.get("name")
        for elem in root.findall(".//{*}Parameter")
        if elem.get("name")
    }


def _parameter_values(root: ET.Element) -> dict[str, tuple[str, str]]:
    result = {}
    for param in root.findall(".//{*}Parameter"):
        name = param.get("name")
        type_elem = next(iter(param), None)
        if name and type_elem is not None:
            type_name = type_elem.tag.split("}", 1)[-1]
            result[name] = (type_name, type_elem.get("value"))
    return result


def test_generate_parameter_set_uses_zero_based_indexing(tmp_path) -> None:
    architecture_dir = write_ssv_type_coverage_architecture(tmp_path / "arch")
    output_path = tmp_path / "parameters.ssv"
    written = generate_parameter_set(architecture_dir, output_path, COMPOSITION_NAME)

    assert written == output_path
    assert output_path.exists()

    root = ET.parse(output_path).getroot()
    names = _parameter_names(root)

    assert "p.i_list[0]" in names
    assert "p.i_list[1]" in names
    assert "p.b_list[0]" in names
    assert "p.b_list[1]" in names
    assert "p.i_list[2]" not in names

    values = _parameter_values(root)
    assert values["p.r"] == ("Real", "1.5")
    assert values["p.i"] == ("Integer", "7")
    assert values["p.b"] == ("Boolean", "true")
    assert values["p.s"] == ("String", "abc")
    assert values["p.i_list[0]"] == ("Integer", "1")
    assert values["p.b_list[0]"] == ("Boolean", "true")
