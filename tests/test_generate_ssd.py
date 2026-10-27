from __future__ import annotations

from pathlib import Path

import pytest
from pyssp_standard import SSD, System

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
          port def ParameterInterface;
          attribute def ParameterSet;

          port def SourceParameters :> ParameterInterface {
            attribute gains : Real[2];
          }

          part def Source {
            in port parameters : SourceParameters;
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
        assert component.source == ""


def test_generate_ssd_rejects_retired_parameter_set_attribute(tmp_path: Path) -> None:
    """The legacy external SSV pointer is replaced by SysML-defined sets."""
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
    with pytest.raises(ValueError, match="pyssp_parameter_set is no longer supported"):
        generate_ssd(architecture_dir, output_path, COMPOSITION_NAME)


BOUNDARY_MODEL = """
        package Example {{
          port def Signal {{
            attribute x : Real;
          }}

          part def Source {{
            out port sig : Signal;
          }}

          part def Sink {{
            in port sigIn : Signal;
            out port sig : Signal;
          }}

          part def Inner {{
            in port u : Signal;
            out port v : Signal;
            part src : Source;
            part dst : Sink;
            connect u to src.sig;
            connect src.sig to dst.sigIn;
            connect dst.sig to v;
          }}

          part def {COMPOSITION_NAME} {{
            out port y : Signal;
            part inner : Inner;
            connect inner.v to y;
          }}
        }}
        """


def test_generate_ssd_wires_system_boundary(tmp_path: Path) -> None:
    """A bare connection end emits an SSD connection without an element."""
    architecture_dir = tmp_path / "arch"
    write_model(
        architecture_dir / "model.sysml",
        BOUNDARY_MODEL.format(COMPOSITION_NAME=COMPOSITION_NAME),
    )

    output_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(architecture_dir, output_path, COMPOSITION_NAME)

    with SSD(output_path, mode="r") as ssd:
        top = ssd.xml.system
        assert [(connector.name, connector.kind) for connector in top.connectors] == [
            ("y.x", "output")
        ]
        assert [
            (c.start_element, c.start_connector, c.end_element, c.end_connector)
            for c in top.connections
        ] == [("inner", "v.x", None, "y.x")]

        inner = top.elements[0]
        assert isinstance(inner, System)
        assert [(connector.name, connector.kind) for connector in inner.connectors] == [
            ("u.x", "input"),
            ("v.x", "output"),
        ]
        assert [
            (c.start_element, c.start_connector, c.end_element, c.end_connector)
            for c in inner.connections
        ] == [
            (None, "u.x", "src", "sig.x"),
            ("src", "sig.x", "dst", "sigIn.x"),
            ("dst", "sig.x", None, "v.x"),
        ]


def test_generate_ssd_rejects_boundary_port_wrong_direction(tmp_path: Path) -> None:
    """A boundary port used as the start of a connection must be an input."""
    architecture_dir = tmp_path / "arch"
    write_model(
        architecture_dir / "model.sysml",
        """
        package Example {
          port def Signal {
            attribute x : Real;
          }

          part def Source {
            out port sig : Signal;
          }

          part def SystemComposition {
            in port y : Signal;
            part src : Source;
            connect src.sig to y;
          }
        }
        """,
    )

    with pytest.raises(ValueError, match="used as the end of a connection"):
        generate_ssd(
            architecture_dir, tmp_path / "SystemStructure.ssd", COMPOSITION_NAME
        )


def test_generate_ssd_rejects_boundary_to_boundary_connection(tmp_path: Path) -> None:
    """A connection between two boundary ports does not cross a subpart."""
    architecture_dir = tmp_path / "arch"
    write_model(
        architecture_dir / "model.sysml",
        """
        package Example {
          port def Signal {
            attribute x : Real;
          }

          part def SystemComposition {
            in port u : Signal;
            out port v : Signal;
            connect u to v;
          }
        }
        """,
    )

    with pytest.raises(ValueError, match="links two boundary ports"):
        generate_ssd(
            architecture_dir, tmp_path / "SystemStructure.ssd", COMPOSITION_NAME
        )
