from __future__ import annotations

import xml.etree.ElementTree as ET

from pyssp_sysml2.fmi import generate_model_descriptions
from tests.sysml_test_models import COMPOSITION_NAME, write_fmi_list_type_architecture


def _variable_names(root: ET.Element) -> set[str]:
    return {
        elem.get("name")
        for elem in root.findall(".//ScalarVariable")
        if elem.get("name")
    }


def _variable_map(root: ET.Element) -> dict[str, ET.Element]:
    vars_by_name = {}
    for elem in root.findall(".//ScalarVariable"):
        name = elem.get("name")
        if name:
            vars_by_name[name] = elem
    return vars_by_name


def test_generate_model_descriptions_from_small_snippet(tmp_path) -> None:
    architecture_dir = write_fmi_list_type_architecture(tmp_path / "arch")
    output_dir = tmp_path / "model_descriptions"

    written = generate_model_descriptions(
        architecture_path=architecture_dir,
        output_dir=output_dir,
        composition=COMPOSITION_NAME,
    )

    assert len(written) == 1

    a_path = output_dir / "Comp" / "modelDescription.xml"
    assert a_path in written

    root = ET.parse(a_path).getroot()
    assert root.get("generationTool") == "pyssp_sysml2 tooling"

    names = _variable_names(root)
    assert "int_list[0]" in names
    assert "int_list[1]" in names
    assert "bool_list[0]" in names
    assert "status.ok" in names

    var_map = _variable_map(root)
    assert var_map["int_list[0]"].get("causality") == "parameter"
    assert var_map["int_list[0]"].get("variability") == "fixed"
    assert var_map["status.ok"].get("causality") == "output"

    int_list_type = next(iter(var_map["int_list[0]"])).tag
    bool_list_type = next(iter(var_map["bool_list[0]"])).tag
    assert int_list_type == "Integer"
    assert bool_list_type == "Boolean"
    assert next(iter(var_map["int_list[0]"])).get("start") == "1"
    assert next(iter(var_map["bool_list[0]"])).get("start") == "true"
