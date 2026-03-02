from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from pycps_sysmlv2 import SysMLParser

from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.sync import sync_sysml_from_ssd

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "aircraft_subset"
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


def test_sync_ssd_changes_are_reflected_in_sysml(tmp_path: Path) -> None:
    arch_dir = tmp_path / "arch"
    shutil.copytree(FIXTURE_DIR, arch_dir)
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(arch_dir, ssd_path, "AircraftComposition")

    _remove_connections(
        ssd_path,
        start_element="environment",
        start_connector_prefix="location.",
        end_element="autopilot",
        end_connector_prefix="currentLocation.",
    )

    written = sync_sysml_from_ssd(arch_dir, ssd_path, "AircraftComposition")
    assert any(path.name == "composition.sysml" for path in written)

    architecture = SysMLParser(arch_dir).parse()
    system = architecture.get_part("AircraftComposition")
    keys = {
        (conn.src_component, conn.src_port, conn.dst_component, conn.dst_port)
        for conn in system.connections
    }
    assert ("environment", "location", "autopilot", "currentLocation") not in keys
    assert len(keys) == 4


def test_sync_ssd_rejects_partial_port_mapping(tmp_path: Path) -> None:
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(FIXTURE_DIR, ssd_path, "AircraftComposition")

    _remove_connections(
        ssd_path,
        start_element="environment",
        start_connector_prefix="orientation.roll_deg",
        end_element="autopilot",
        end_connector_prefix="currentOrientation.roll_deg",
    )

    with pytest.raises(ValueError, match="partial/invalid attribute mapping"):
        sync_sysml_from_ssd(FIXTURE_DIR, ssd_path, "AircraftComposition")
