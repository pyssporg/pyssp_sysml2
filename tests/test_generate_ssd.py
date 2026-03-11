from __future__ import annotations

from pathlib import Path

from pycps_sysmlv2 import NodeType, SysMLParser
from pyssp_standard.ssd import SSD

from pyssp_sysml2.ssd import build_ssd
from tests.test_utils import COMPOSITION_NAME, write_model



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
    """Generated SSD contains expected connectors, parameters, and expanded connections."""
    architecture_dir = tmp_path / "arch"
    architecture_dir.mkdir(parents=True, exist_ok=True)

    write_model(
        architecture_dir / "ports.sysml",
        """
        package Example {
          port def Signal {
            attribute mode: Integer;
            attribute x: Real;
          }
        }
        """,
    )

    write_model(
        architecture_dir / "parts.sysml",
        """
        package Example {
          part def Source {
            attribute gains = [1.0, 2.0];
            out port sig : Signal;
          }

          part def Sink {
            in port sigIn : Signal;
          }
        }
        """,
    )

    write_model(
        architecture_dir / "composition.sysml",
        f"""
        package Example {{
          part def {COMPOSITION_NAME} {{
            part src : Source;
            part dst : Sink;

            connect src.sig to dst.sigIn;
          }}
        }}
        """,
    )

    output_path = tmp_path / "SystemStructure.ssd"
    system = SysMLParser(architecture_dir).parse().get_def(NodeType.Part, COMPOSITION_NAME)

    with SSD(output_path, mode="w") as ssd:
        build_ssd(ssd, system)

    assert _ssd_summary(output_path) == [
        "component dst",
        "  input:sigIn.mode:Integer",
        "  input:sigIn.x:Real",
        "component src",
        "  output:sig.mode:Integer",
        "  output:sig.x:Real",
        "  parameter:gains[0]:Real",
        "  parameter:gains[1]:Real",
        "connection src.sig.mode -> dst.sigIn.mode",
        "connection src.sig.x -> dst.sigIn.x",
    ]
