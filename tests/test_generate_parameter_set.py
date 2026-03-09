from __future__ import annotations

from pyssp_standard.ssv import SSV

from pyssp_sysml2.ssv import generate_parameter_set
from tests.sysml_test_models import COMPOSITION_NAME, write_ssv_type_coverage_architecture


def _parameter_summary(ssv_path) -> list[str]:
    with SSV(ssv_path, mode="r") as ssv:
        return sorted(
            f"{parameter['name']}:{parameter['type_name']}:{parameter['type_value'].parameter.get('value')}"
            for parameter in ssv.parameters
        )


def test_generate_parameter_set_uses_zero_based_indexing(tmp_path) -> None:
    architecture_dir = write_ssv_type_coverage_architecture(tmp_path / "arch")
    output_path = tmp_path / "parameters.ssv"
    written = generate_parameter_set(architecture_dir, output_path, COMPOSITION_NAME)

    assert written == output_path
    assert output_path.exists()

    assert _parameter_summary(output_path) == [
        "p.b:Boolean:true",
        "p.b_list[0]:Boolean:true",
        "p.b_list[1]:Boolean:false",
        "p.i:Integer:7",
        "p.i_list[0]:Integer:1",
        "p.i_list[1]:Integer:2",
        "p.r:Real:1.5",
        "p.s:String:abc",
    ]
