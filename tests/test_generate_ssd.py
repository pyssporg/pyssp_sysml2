from __future__ import annotations

from pycps_sysmlv2 import SysMLParser
from pyssp_standard.ssd import SSD

from pyssp_sysml2.ssd import build_ssd
from tests.sysml_test_models import COMPOSITION_NAME, write_connected_triplet_architecture


def _ssd_summary(ssd_path) -> list[str]:
    with SSD(ssd_path, mode="r") as ssd:
        assert ssd.system is not None

        lines = []
        for component in sorted(ssd.system.elements, key=lambda element: element.name):
            connector_summaries = sorted(
                f"{connector.kind}:{connector.name}:{connector.type_.__class__.__name__[4:]}"
                for connector in component.connectors
            )
            lines.append(f"component {component.name}")
            lines.extend(f"  {summary}" for summary in connector_summaries)

        for connection in sorted(
            ssd.system.connections,
            key=lambda conn: (
                conn.start_element,
                conn.start_connector,
                conn.end_element,
                conn.end_connector,
            ),
        ):
            lines.append(
                "connection "
                f"{connection.start_element}.{connection.start_connector}"
                f" -> {connection.end_element}.{connection.end_connector}"
            )

        return lines


def test_generate_ssd_from_small_snippet(tmp_path) -> None:
    architecture_dir = write_connected_triplet_architecture(tmp_path / "arch")
    output_path = tmp_path / "SystemStructure.ssd"
    system = SysMLParser(architecture_dir).parse().get_part(COMPOSITION_NAME)

    with SSD(output_path, mode="w") as ssd:
        build_ssd(ssd, system)

    assert _ssd_summary(output_path) == [
        "component a",
        "  output:cmd.mode:Integer",
        "  output:cmd.pitch:Real",
        "  parameter:gains[0]:Real",
        "  parameter:gains[1]:Real",
        "  parameter:gains[2]:Real",
        "component b",
        "  input:cmdIn.mode:Integer",
        "  input:cmdIn.pitch:Real",
        "  output:pos.x:Real",
        "  output:pos.y:Real",
        "component c",
        "  input:cmdIn.mode:Integer",
        "  input:cmdIn.pitch:Real",
        "  input:posIn.x:Real",
        "  input:posIn.y:Real",
        "connection a.cmd.mode -> b.cmdIn.mode",
        "connection a.cmd.pitch -> b.cmdIn.pitch",
        "connection b.pos.x -> c.posIn.x",
        "connection b.pos.y -> c.posIn.y",
    ]
