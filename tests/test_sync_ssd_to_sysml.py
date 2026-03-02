from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from pycps_sysmlv2 import SysMLParser

from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.sync import sync_sysml_from_ssd
from tests.sysml_test_models import (
    COMPOSITION_NAME,
    write_connected_triplet_architecture,
    write_sync_pair_architecture,
)

SSD_NS = {"ssd": "http://ssp-standard.org/SSP1/SystemStructureDescription"}


def _remove_connections(
    ssd_path: Path,
    *,
    start_element: str,
    start_connector_prefix: str,
    end_element: str,
    end_connector_prefix: str,
) -> None:
    tree = ET.parse(ssd_path)
    root = tree.getroot()
    connections_parent = root.find(".//ssd:Connections", SSD_NS)
    assert connections_parent is not None
    for connection in list(connections_parent):
        if (
            connection.get("startElement") == start_element
            and connection.get("startConnector", "").startswith(start_connector_prefix)
            and connection.get("endElement") == end_element
            and connection.get("endConnector", "").startswith(end_connector_prefix)
        ):
            connections_parent.remove(connection)
    tree.write(ssd_path, encoding="utf-8", xml_declaration=True)


def _rewrite_connections(
    ssd_path: Path,
    rewrite_fn,
) -> None:
    tree = ET.parse(ssd_path)
    root = tree.getroot()
    connections_parent = root.find(".//ssd:Connections", SSD_NS)
    assert connections_parent is not None
    for connection in list(connections_parent):
        rewrite_fn(connection)
    tree.write(ssd_path, encoding="utf-8", xml_declaration=True)


def test_sync_ssd_changes_are_reflected_in_sysml(tmp_path: Path) -> None:
    arch_dir = write_connected_triplet_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(arch_dir, ssd_path, COMPOSITION_NAME)

    _remove_connections(
        ssd_path,
        start_element="b",
        start_connector_prefix="pos.",
        end_element="c",
        end_connector_prefix="posIn.",
    )

    written = sync_sysml_from_ssd(arch_dir, ssd_path, COMPOSITION_NAME)
    assert any(path.name == "composition.sysml" for path in written)

    architecture = SysMLParser(arch_dir).parse()
    system = architecture.get_part(COMPOSITION_NAME)
    keys = {
        (conn.src_component, conn.src_port, conn.dst_component, conn.dst_port)
        for conn in system.connections
    }
    assert ("b", "pos", "c", "posIn") not in keys
    assert len(keys) == 1


def test_sync_ssd_is_idempotent_when_no_changes(tmp_path: Path) -> None:
    arch_dir = write_sync_pair_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(arch_dir, ssd_path, COMPOSITION_NAME)

    written = sync_sysml_from_ssd(arch_dir, ssd_path, COMPOSITION_NAME)
    assert any(path.name == "composition.sysml" for path in written)

    architecture = SysMLParser(arch_dir).parse()
    system = architecture.get_part(COMPOSITION_NAME)
    keys = {
        (conn.src_component, conn.src_port, conn.dst_component, conn.dst_port)
        for conn in system.connections
    }
    assert keys == {("src", "outSig", "dst", "inSig")}


def test_sync_ssd_rejects_partial_port_mapping(tmp_path: Path) -> None:
    arch_dir = write_sync_pair_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(arch_dir, ssd_path, COMPOSITION_NAME)

    _remove_connections(
        ssd_path,
        start_element="src",
        start_connector_prefix="outSig.x",
        end_element="dst",
        end_connector_prefix="inSig.x",
    )

    with pytest.raises(ValueError, match="partial/invalid attribute mapping"):
        sync_sysml_from_ssd(arch_dir, ssd_path, COMPOSITION_NAME)


def test_sync_ssd_rejects_attribute_remapping(tmp_path: Path) -> None:
    arch_dir = write_sync_pair_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(arch_dir, ssd_path, COMPOSITION_NAME)

    def rewrite(connection: ET.Element) -> None:
        if (
            connection.get("startElement") == "src"
            and connection.get("startConnector") == "outSig.x"
            and connection.get("endElement") == "dst"
            and connection.get("endConnector") == "inSig.x"
        ):
            connection.set("endConnector", "inSig.y")

    _rewrite_connections(ssd_path, rewrite)

    with pytest.raises(ValueError, match="attribute remapping"):
        sync_sysml_from_ssd(arch_dir, ssd_path, COMPOSITION_NAME)


def test_sync_ssd_rejects_unknown_component(tmp_path: Path) -> None:
    arch_dir = write_sync_pair_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(arch_dir, ssd_path, COMPOSITION_NAME)

    def rewrite(connection: ET.Element) -> None:
        if connection.get("startElement") == "src":
            connection.set("startElement", "ghost")

    _rewrite_connections(ssd_path, rewrite)

    with pytest.raises(ValueError, match="unknown source component"):
        sync_sysml_from_ssd(arch_dir, ssd_path, COMPOSITION_NAME)


def test_sync_ssd_rejects_unknown_port(tmp_path: Path) -> None:
    arch_dir = write_sync_pair_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(arch_dir, ssd_path, COMPOSITION_NAME)

    def rewrite(connection: ET.Element) -> None:
        if connection.get("endElement") == "dst" and connection.get("endConnector") == "inSig.x":
            connection.set("endConnector", "unknownPort.x")
        if connection.get("endElement") == "dst" and connection.get("endConnector") == "inSig.y":
            connection.set("endConnector", "unknownPort.y")

    _rewrite_connections(ssd_path, rewrite)

    with pytest.raises(ValueError, match="Unknown destination port"):
        sync_sysml_from_ssd(arch_dir, ssd_path, COMPOSITION_NAME)


def test_sync_ssd_rejects_incompatible_ports(tmp_path: Path) -> None:
    arch_dir = write_connected_triplet_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(arch_dir, ssd_path, COMPOSITION_NAME)

    def rewrite(connection: ET.Element) -> None:
        if connection.get("endElement") == "c" and connection.get("endConnector") == "posIn.x":
            connection.set("endConnector", "cmdIn.x")
        if connection.get("endElement") == "c" and connection.get("endConnector") == "posIn.y":
            connection.set("endConnector", "cmdIn.y")

    _rewrite_connections(ssd_path, rewrite)

    with pytest.raises(ValueError, match="incompatible ports"):
        sync_sysml_from_ssd(arch_dir, ssd_path, COMPOSITION_NAME)


def test_sync_ssd_writes_to_output_architecture_dir(tmp_path: Path) -> None:
    arch_dir = write_sync_pair_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    out_dir = tmp_path / "synced"
    generate_ssd(arch_dir, ssd_path, COMPOSITION_NAME)

    _remove_connections(
        ssd_path,
        start_element="src",
        start_connector_prefix="outSig.",
        end_element="dst",
        end_connector_prefix="inSig.",
    )

    written = sync_sysml_from_ssd(
        arch_dir, ssd_path, COMPOSITION_NAME, output_architecture_dir=out_dir
    )
    assert all(str(path).startswith(str(out_dir)) for path in written)
    assert (out_dir / "composition.sysml").exists()
