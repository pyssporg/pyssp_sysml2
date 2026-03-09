from __future__ import annotations

from pathlib import Path

import pytest
from pycps_sysmlv2 import SysMLParser
from pyssp_standard.ssd import Component, Connection, SSD

from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.sync import sync_sysml_from_ssd
from tests.test_utils import COMPOSITION_NAME, write_model


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
    composition = SysMLParser(architecture_path).parse().get_part(COMPOSITION_NAME)

    lines = []
    for part_name in sorted(composition.parts):
        part_ref = composition.parts[part_name]
        lines.append(f"part {part_name}:{part_ref.part_name}")

    for connection in sorted(
        composition.connections,
        key=lambda conn: (conn.src_component, conn.src_port, conn.dst_component, conn.dst_port),
    ):
        lines.append(
            "connect "
            f"{connection.src_component}.{connection.src_port}"
            f"->{connection.dst_component}.{connection.dst_port}"
        )
    return lines


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

    assert _composition_summary(output_dir) == [
        "part dst:AltSink",
        "part src:Source",
        "connect src.outSig->dst.inSig",
    ]


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

    assert _composition_summary(output_dir) == [
        "part alt:AltSink",
        "part dst:Sink",
        "part src:Source",
        "connect src.outSig->alt.inSig",
        "connect src.outSig->dst.inSig",
    ]


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
