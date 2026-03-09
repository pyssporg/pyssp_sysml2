from __future__ import annotations

from pathlib import Path

from pyssp_standard.ssv import SSV

from pyssp_sysml2.ssv import generate_parameter_set
from tests.test_utils import COMPOSITION_NAME, write_model


def _parameter_summary(ssv_path) -> list[str]:
    with SSV(ssv_path, mode="r") as ssv:
        return sorted(
            f"{parameter['name']}:{parameter['type_name']}:{parameter['type_value'].parameter.get('value')}"
            for parameter in ssv.parameters
        )


def test_generate_parameter_set_uses_zero_based_indexing(tmp_path) -> None:
    """List attributes are exported to SSV parameters with zero-based indices."""
    architecture_dir = tmp_path / "arch"
    architecture_dir.mkdir(parents=True, exist_ok=True)

    write_model(
        architecture_dir / "parts.sysml",
        f"""
        package Example {{
          part def Params {{
            attribute i_list = [1, 2];
          }}

          part def {COMPOSITION_NAME} {{
            part p : Params;
          }}
        }}
        """,
    )

    output_path = tmp_path / "parameters.ssv"
    written = generate_parameter_set(architecture_dir, output_path, COMPOSITION_NAME)

    assert written == output_path
    assert output_path.exists()

    assert _parameter_summary(output_path) == [
        "p.i_list[0]:Integer:1",
        "p.i_list[1]:Integer:2",
    ]


def test_generate_parameter_set_formats_scalar_types(tmp_path) -> None:
    """Scalar Real/Integer/Boolean/String attributes are formatted correctly in SSV."""

    write_model(
        tmp_path / "arch" / "parts.sysml",
        f"""
        package Example {{
          part def Params {{
            attribute r = 1.5;
            attribute i = 7;
            attribute b = true;
            attribute s = "abc";
          }}

          part def {COMPOSITION_NAME} {{
            part p : Params;
          }}
        }}
        """,
    )

    output_path = tmp_path / "parameters.ssv"
    generate_parameter_set(tmp_path / "arch", output_path, COMPOSITION_NAME)

    assert _parameter_summary(output_path) == [
        "p.b:Boolean:true",
        "p.i:Integer:7",
        "p.r:Real:1.5",
        "p.s:String:abc",
    ]
