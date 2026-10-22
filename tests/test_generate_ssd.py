from __future__ import annotations

from pathlib import Path

from pyssp_standard.ssd import SSD

from pyssp_sysml2.ssd import build_ssd, generate_ssd
from pyssp_sysml2.sysml_model import load
from tests.test_utils import COMPOSITION_NAME, write_model



def _ssd_summary(ssd_path) -> list[str]:
    with SSD(ssd_path, mode="r") as ssd:
        assert ssd.xml.system is not None

        lines = []
        for component in sorted(ssd.xml.system.elements, key=lambda element: element.name):
            connector_summaries = sorted(
                f"{connector.kind}:{connector.name}:{connector.type_name}"
                for connector in component.connectors
            )
            lines.append(f"component {component.name}")
            lines.extend(f"  {summary}" for summary in connector_summaries)

        for connection in sorted(
            ssd.xml.system.connections,
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
            attribute gains = (1.0, 2.0);
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
    architecture = load(architecture_dir)
    system = architecture.get_part_def(COMPOSITION_NAME)

    with SSD(output_path, mode="w") as ssd:
        build_ssd(ssd, system, architecture)

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


def test_generate_ssd_writes_core_ssd_metadata(tmp_path: Path) -> None:
    """Generated SSD sets the expected top-level metadata and component fields."""
    architecture_dir = tmp_path / "arch"
    architecture_dir.mkdir(parents=True, exist_ok=True)

    write_model(
        architecture_dir / "model.sysml",
        f"""
        package Example {{
          port def Signal {{
            attribute x: Real;
          }}

          part def Source {{
            out port outSig : Signal;
          }}

          part def {COMPOSITION_NAME} {{
            part src : Source;
          }}
        }}
        """,
    )

    output_path = tmp_path / "SystemStructure.ssd"
    architecture = load(architecture_dir)
    system = architecture.get_part_def(COMPOSITION_NAME)

    with SSD(output_path, mode="w") as ssd:
        build_ssd(ssd, system, architecture)

    assert _ssd_summary(output_path) == [
        "component src",
        "  output:outSig.x:Real",
    ]

    with SSD(output_path, mode="r") as ssd:
        assert ssd.xml.name == COMPOSITION_NAME
        assert ssd.xml.version == "1.0"
        assert ssd.xml.default_experiment is not None
        assert ssd.xml.default_experiment.start_time == 0
        assert ssd.xml.default_experiment.stop_time == 3600
        assert ssd.xml.system is not None
        assert len(ssd.xml.system.elements) == 1
        component = ssd.xml.system.elements[0]
        assert component.name == "src"
        assert component.component_type == "application/x-fmu-sharedlibrary"
        assert component.source == "resources/Source.fmu"


def test_generate_ssd_keeps_legacy_parameter_set_binding(tmp_path: Path) -> None:
    """Existing flat-attribute models still use pyssp_parameter_set semantics."""
    architecture_dir = tmp_path / "arch"
    write_model(
        architecture_dir / "model.sysml",
        f"""
        package Example {{
          part def Gain {{
            attribute k : Real = 3.0;
          }}

          part def {COMPOSITION_NAME} {{
            part gain : Gain;
            attribute pyssp_parameter_set : String = "parameters.ssv";
          }}
        }}
        """,
    )

    output_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(architecture_dir, output_path, COMPOSITION_NAME)

    with SSD(output_path, mode="r") as ssd:
        [binding] = ssd.xml.system.parameter_bindings
        assert binding.source == "parameters.ssv"
        assert binding.prefix is None
        assert binding.parameter_mapping is None
        component = ssd.xml.system.elements[0]
        assert [(connector.name, connector.kind) for connector in component.connectors] == [
            ("k", "parameter")
        ]
