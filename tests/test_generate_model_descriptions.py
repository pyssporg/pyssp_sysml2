from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from pyssp_sysml2.fmi import generate_model_descriptions
from tests.test_utils import COMPOSITION_NAME, write_model



def _model_description_summary(path) -> list[str]:
    root = ET.parse(path).getroot()
    scalar_variables = [
        elem
        for elem in root.findall(".//ScalarVariable")
        if elem.get("name") is not None
    ]
    outputs = {
        int(elem.get("index"))
        for elem in root.findall("./ModelStructure/Outputs/Unknown")
        if elem.get("index") is not None
    }

    lines = [f"generationTool:{root.get('generationTool')}"]
    for index, variable in enumerate(scalar_variables, start=1):
        type_elem = next(iter(variable), None)
        assert type_elem is not None
        tag = type_elem.tag.split("}", 1)[-1]
        start = type_elem.get("start")
        output_flag = "output" if index in outputs else "nonoutput"
        lines.append(
            f"{variable.get('name')}|{variable.get('causality')}|"
            f"{variable.get('variability')}|{tag}|{start}|{variable.get('valueReference')}|{output_flag}"
        )
    return lines


def test_generate_model_descriptions_from_small_snippet(tmp_path) -> None:
    """Model description export preserves expected FMI variables and output markers."""
    architecture_dir = tmp_path / "arch"
    architecture_dir.mkdir(parents=True, exist_ok=True)

    write_model(
        architecture_dir / "ports.sysml",
        """
        package Example {
          port def Status {
            attribute ok: Boolean;
          }
        }
        """,
    )

    write_model(
        architecture_dir / "parts.sysml",
        f"""
        package Example {{
          part def Comp {{
            attribute int_list = [1, 2];
            attribute bool_list = [True, False];
            out port status : Status;
          }}

          part def {COMPOSITION_NAME} {{
            part c : Comp;
          }}
        }}
        """,
    )

    output_dir = tmp_path / "model_descriptions"

    written = generate_model_descriptions(
        architecture_path=architecture_dir,
        output_dir=output_dir,
        composition=COMPOSITION_NAME,
    )

    assert len(written) == 1

    a_path = output_dir / "Comp" / "modelDescription.xml"
    assert a_path in written

    assert _model_description_summary(a_path) == [
        "generationTool:pyssp_sysml2 tooling",
        "int_list[0]|parameter|fixed|Integer|1|0|nonoutput",
        "int_list[1]|parameter|fixed|Integer|2|1|nonoutput",
        "bool_list[0]|parameter|fixed|Boolean|true|2|nonoutput",
        "bool_list[1]|parameter|fixed|Boolean|false|3|nonoutput",
        "status.ok|output|None|Boolean|None|4|output",
    ]
