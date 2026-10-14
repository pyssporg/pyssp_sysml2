from __future__ import annotations

from pathlib import Path

import pytest
from textwrap import dedent

from pyssp_standard.common_content_ssc import TypeBoolean, TypeReal
from pyssp_standard.ssd import Component, Connection, Connector, SSD

from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.sync import sync_sysml_from_ssd
from pyssp_sysml2.sysml_model import load
from tests.test_utils import COMPOSITION_NAME, write_bootstrap_ssd, write_model


def _write_sync_architecture(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)

    write_model(
        root / "model.sysml",
        f"""
        package Example {{
          port def Signal {{
            attribute x: Real;
            attribute y: Real;
          }}

          part def Source {{
            out port outSig : Signal;
          }}

          part def Sink {{
            in port inSig : Signal;
          }}

          part def AltSink {{
            in port inSig : Signal;
          }}

          part def {COMPOSITION_NAME} {{
            part src : Source;
            part dst : Sink;
            connect src.outSig to dst.inSig;
          }}
        }}
        """,
    )
    return root


def _composition_summary(architecture_path: Path) -> list[str]:
    composition = load(architecture_path).get_part_def(COMPOSITION_NAME)

    lines = []
    for part_name in sorted(composition.parts):
        part_usage = composition.parts[part_name]
        lines.append(f"part {part_name}:{part_usage.type_name}")

    for connection in sorted(
        composition.connections.values(),
        key=lambda conn: (
            conn.source_part,
            conn.source_port,
            conn.destination_part,
            conn.destination_port,
        ),
    ):
        lines.append(
            "connect "
            f"{connection.source_part}.{connection.source_port}"
            f"->{connection.destination_part}.{connection.destination_port}"
        )
    return lines


def _architecture_text(architecture_path: Path) -> str:
    files = load(architecture_path).export_declared()
    return "\n".join(files[name] for name in sorted(files))


def test_sync_sysml_from_ssd_removes_connection_deleted_in_ssd(tmp_path: Path) -> None:
    """Sync removes composition connections that were removed from the SSD."""
    architecture_dir = _write_sync_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(architecture_dir, ssd_path, COMPOSITION_NAME)

    with SSD(ssd_path, mode="a") as ssd:
        assert ssd.system is not None
        ssd.system.connections = []

    output_dir = tmp_path / "synced"
    written = sync_sysml_from_ssd(
        architecture_path=architecture_dir,
        ssd_path=ssd_path,
        composition=COMPOSITION_NAME,
        output_architecture_dir=output_dir,
    )

    assert all(path.exists() for path in written)
    assert _composition_summary(output_dir) == [
        "part dst:Sink",
        "part src:Source",
    ]


def test_sync_sysml_from_ssd_updates_part_type_from_component_source(tmp_path: Path) -> None:
    """Sync updates a composition part type when the SSD component source changes."""
    architecture_dir = _write_sync_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(architecture_dir, ssd_path, COMPOSITION_NAME)

    with SSD(ssd_path, mode="a") as ssd:
        assert ssd.system is not None
        dst_component = next(element for element in ssd.system.elements if element.name == "dst")
        dst_component.source = "resources/AltSink.fmu"

    output_dir = tmp_path / "synced"
    sync_sysml_from_ssd(
        architecture_path=architecture_dir,
        ssd_path=ssd_path,
        composition=COMPOSITION_NAME,
        output_architecture_dir=output_dir,
    )

    assert _architecture_text(output_dir) == dedent(
        f"""
        package Example {{
          port def Signal {{
            attribute x : Real;
            attribute y : Real;
          }}

          part def AltSink {{
            in port inSig : Signal;
          }}

          part def Sink {{
            in port inSig : Signal;
          }}

          part def Source {{
            out port outSig : Signal;
          }}

          part def {COMPOSITION_NAME} {{
            part dst : AltSink;
            part src : Source;
            connect src.outSig to dst.inSig;
          }}
        }}
        """
    ).strip() + "\n"


def test_sync_sysml_from_ssd_rejects_partial_attribute_mapping(tmp_path: Path) -> None:
    """Sync fails when SSD maps only a subset of required port attributes."""
    architecture_dir = _write_sync_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(architecture_dir, ssd_path, COMPOSITION_NAME)

    with SSD(ssd_path, mode="a") as ssd:
        assert ssd.system is not None
        ssd.system.connections = [
            conn
            for conn in ssd.system.connections
            if conn.start_connector.endswith(".x")
        ]

    with pytest.raises(ValueError, match="partial/invalid attribute mapping"):
        sync_sysml_from_ssd(
            architecture_path=architecture_dir,
            ssd_path=ssd_path,
            composition=COMPOSITION_NAME,
        )


def test_sync_sysml_from_ssd_adds_part_from_ssd_component(tmp_path: Path) -> None:
    """Sync adds a new composition part when a new SSD component is introduced."""
    architecture_dir = _write_sync_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(architecture_dir, ssd_path, COMPOSITION_NAME)

    with SSD(ssd_path, mode="a") as ssd:
        assert ssd.system is not None
        alt = Component()
        alt.name = "alt"
        alt.source = "resources/AltSink.fmu"
        ssd.system.elements.append(alt)
        ssd.system.connections.extend(
            [
                Connection(
                    start_element="src",
                    start_connector="outSig.x",
                    end_element="alt",
                    end_connector="inSig.x",
                ),
                Connection(
                    start_element="src",
                    start_connector="outSig.y",
                    end_element="alt",
                    end_connector="inSig.y",
                ),
            ]
        )

    output_dir = tmp_path / "synced"
    sync_sysml_from_ssd(
        architecture_path=architecture_dir,
        ssd_path=ssd_path,
        composition=COMPOSITION_NAME,
        output_architecture_dir=output_dir,
    )

    assert _architecture_text(output_dir) == dedent(
        f"""
        package Example {{
          port def Signal {{
            attribute x : Real;
            attribute y : Real;
          }}

          part def AltSink {{
            in port inSig : Signal;
          }}

          part def Sink {{
            in port inSig : Signal;
          }}

          part def Source {{
            out port outSig : Signal;
          }}

          part def {COMPOSITION_NAME} {{
            part alt : AltSink;
            part dst : Sink;
            part src : Source;
            connect src.outSig to alt.inSig;
            connect src.outSig to dst.inSig;
          }}
        }}
        """
    ).strip() + "\n"


def test_sync_sysml_from_ssd_removes_part_missing_from_ssd_components(tmp_path: Path) -> None:
    """Sync removes composition parts that are no longer present in SSD components."""
    architecture_dir = _write_sync_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(architecture_dir, ssd_path, COMPOSITION_NAME)

    with SSD(ssd_path, mode="a") as ssd:
        assert ssd.system is not None
        ssd.system.elements = [element for element in ssd.system.elements if element.name != "dst"]
        ssd.system.connections = []

    output_dir = tmp_path / "synced"
    sync_sysml_from_ssd(
        architecture_path=architecture_dir,
        ssd_path=ssd_path,
        composition=COMPOSITION_NAME,
        output_architecture_dir=output_dir,
    )

    assert _composition_summary(output_dir) == [
        "part src:Source",
    ]


def test_sync_sysml_from_ssd_bootstraps_architecture_when_sysml_is_missing(tmp_path: Path) -> None:
    """Sync can recover a SysML architecture directly from SSD when no .sysml files exist."""
    architecture_dir = tmp_path / "empty_arch"
    architecture_dir.mkdir(parents=True, exist_ok=True)
    ssd_path = write_bootstrap_ssd(tmp_path / "SystemStructure.ssd")

    written = sync_sysml_from_ssd(
        architecture_path=architecture_dir,
        ssd_path=ssd_path,
        composition=COMPOSITION_NAME,
    )

    assert written == [architecture_dir / "architecture.sysml"]
    assert _architecture_text(architecture_dir) == dedent(
        """
        package RecoveredFromSSD {
          port def Port_1 {
            attribute x : Real;
            attribute y : Real;
          }

          part def Sink {
            in port inSig : Port_1;
          }

          part def Source {
            out port outSig : Port_1;
          }

          part def SystemComposition {
            part dst : Sink;
            part src : Source;
            connect src.outSig to dst.inSig;
          }
        }
        """
    ).strip() + "\n"


def test_sync_sysml_from_ssd_preserves_unrelated_definitions_and_file_layout(tmp_path: Path) -> None:
    """Sync updates composition content without dropping unrelated definitions in the same file set."""
    architecture_dir = tmp_path / "arch"
    architecture_dir.mkdir(parents=True, exist_ok=True)

    write_model(
        architecture_dir / "ports.sysml",
        """
        package Example {
          port def Signal {
            attribute x: Real;
            attribute y: Real;
          }

          port def DebugSignal {
            attribute level: Integer;
          }
        }
        """,
    )
    write_model(
        architecture_dir / "parts.sysml",
        """
        package Example {
          part def Source {
            out port outSig : Signal;
          }

          part def Sink {
            in port inSig : Signal;
          }

          part def Utility {
            out port debug : DebugSignal;
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
            connect src.outSig to dst.inSig;
          }}
        }}
        """,
    )

    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(architecture_dir, ssd_path, COMPOSITION_NAME)

    with SSD(ssd_path, mode="a") as ssd:
        assert ssd.system is not None
        ssd.system.connections = []

    output_dir = tmp_path / "synced"
    written = sync_sysml_from_ssd(
        architecture_path=architecture_dir,
        ssd_path=ssd_path,
        composition=COMPOSITION_NAME,
        output_architecture_dir=output_dir,
    )

    assert sorted(path.name for path in written) == ["composition.sysml", "parts.sysml", "ports.sysml"]
    assert _architecture_text(output_dir) == dedent(
        f"""
        package Example {{
          part def {COMPOSITION_NAME} {{
            part dst : Sink;
            part src : Source;
          }}
        }}

        package Example {{
          part def Sink {{
            in port inSig : Signal;
          }}

          part def Source {{
            out port outSig : Signal;
          }}

          part def Utility {{
            out port debug : DebugSignal;
          }}
        }}

        package Example {{
          port def DebugSignal {{
            attribute level : Integer;
          }}

          port def Signal {{
            attribute x : Real;
            attribute y : Real;
          }}
        }}
        """
    ).strip() + "\n"


def test_sync_sysml_from_ssd_synthesizes_part_def_for_unknown_component_source(
    tmp_path: Path,
) -> None:
    """Sync synthesizes a part definition for a new SSD component with an unknown FMU source."""
    architecture_dir = _write_sync_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(architecture_dir, ssd_path, COMPOSITION_NAME)

    with SSD(ssd_path, mode="a") as ssd:
        assert ssd.system is not None
        ext = Component()
        ext.name = "ext"
        ext.source = "resources/ExternalSink.fmu"
        ext.connectors.extend(
            [
                Connector(name="inSig.x", kind="input", type_=TypeReal(unit=None)),
                Connector(name="inSig.y", kind="input", type_=TypeReal(unit=None)),
            ]
        )
        ssd.system.elements.append(ext)
        ssd.system.connections.extend(
            [
                Connection(
                    start_element="src",
                    start_connector="outSig.x",
                    end_element="ext",
                    end_connector="inSig.x",
                ),
                Connection(
                    start_element="src",
                    start_connector="outSig.y",
                    end_element="ext",
                    end_connector="inSig.y",
                ),
            ]
        )

    output_dir = tmp_path / "synced"
    written = sync_sysml_from_ssd(
        architecture_path=architecture_dir,
        ssd_path=ssd_path,
        composition=COMPOSITION_NAME,
        output_architecture_dir=output_dir,
    )

    assert sorted(path.name for path in written) == [
        "inferred_external_parts.sysml",
        "model.sysml",
    ]
    inferred = (output_dir / "inferred_external_parts.sysml").read_text(encoding="utf-8")
    assert "part def ExternalSink" in inferred
    assert "in port inSig : Signal;" in inferred


def test_sync_sysml_from_ssd_synthesizes_new_port_def_for_unmatched_signature(
    tmp_path: Path,
) -> None:
    """Sync creates a port definition when a synthesized component port has no existing match."""
    architecture_dir = _write_sync_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(architecture_dir, ssd_path, COMPOSITION_NAME)

    with SSD(ssd_path, mode="a") as ssd:
        assert ssd.system is not None
        ext_src = Component()
        ext_src.name = "ext_src"
        ext_src.source = "resources/ExternalSource.fmu"
        ext_src.connectors.extend(
            [
                Connector(name="sig.value", kind="output", type_=TypeBoolean()),
            ]
        )
        ext_dst = Component()
        ext_dst.name = "ext_dst"
        ext_dst.source = "resources/ExternalSink.fmu"
        ext_dst.connectors.extend(
            [
                Connector(name="sig.value", kind="input", type_=TypeBoolean()),
            ]
        )
        ssd.system.elements.append(ext_src)
        ssd.system.elements.append(ext_dst)
        ssd.system.connections.extend(
            [
                Connection(
                    start_element="ext_src",
                    start_connector="sig.value",
                    end_element="ext_dst",
                    end_connector="sig.value",
                ),
            ]
        )

    output_dir = tmp_path / "synced"
    written = sync_sysml_from_ssd(
        architecture_path=architecture_dir,
        ssd_path=ssd_path,
        composition=COMPOSITION_NAME,
        output_architecture_dir=output_dir,
    )

    assert sorted(path.name for path in written) == [
        "inferred_external_parts.sysml",
        "model.sysml",
    ]
    inferred = (output_dir / "inferred_external_parts.sysml").read_text(encoding="utf-8")
    assert "part def ExternalSource" in inferred
    assert "part def ExternalSink" in inferred
    assert "port def Port_" in inferred


def test_sync_sysml_from_ssd_rejects_unknown_source_without_synthesis(
    tmp_path: Path,
) -> None:
    """Sync can be told to fail instead of synthesizing unknown FMU sources."""
    architecture_dir = _write_sync_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(architecture_dir, ssd_path, COMPOSITION_NAME)

    with SSD(ssd_path, mode="a") as ssd:
        assert ssd.system is not None
        ext = Component()
        ext.name = "ext"
        ext.source = "resources/ExternalSink.fmu"
        ext.connectors.extend(
            [
                Connector(name="inSig.x", kind="input", type_=TypeReal(unit=None)),
            ]
        )
        ssd.system.elements.append(ext)
        ssd.system.connections.extend(
            [
                Connection(
                    start_element="src",
                    start_connector="outSig.x",
                    end_element="ext",
                    end_connector="inSig.x",
                ),
            ]
        )

    output_dir = tmp_path / "synced"
    with pytest.raises(ValueError, match="references unknown part source 'resources/ExternalSink.fmu'"):
        sync_sysml_from_ssd(
            architecture_path=architecture_dir,
            ssd_path=ssd_path,
            composition=COMPOSITION_NAME,
            output_architecture_dir=output_dir,
            synthesize_external_parts=False,
        )
