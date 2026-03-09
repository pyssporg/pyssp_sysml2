from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from pycps_sysmlv2 import SysMLParser
from pyssp_standard.ssd import Component, Connection, SSD

from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.sync import sync_sysml_from_ssd
from tests.test_utils import COMPOSITION_NAME, write_model


def write_connected_triplet_architecture(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)

    write_model(
        root / "ports.sysml",
        """
        package Example {
          port def Cmd {
            attribute pitch: Real;
            attribute mode: Integer;
          }

          port def Pos {
            attribute x: Real;
            attribute y: Real;
          }
        }
        """,
    )

    write_model(
        root / "parts.sysml",
        """
        package Example {
          part def A {
            out port cmd : Cmd;
          }

          part def B {
            in port cmdIn : Cmd;
            out port pos : Pos;
          }

          part def C {
            in port posIn : Pos;
          }
        }
        """,
    )

    write_model(
        root / "composition.sysml",
        f"""
        package Example {{
          part def {COMPOSITION_NAME} {{
            part a : A;
            part b : B;
            part c : C;

            connect a.cmd to b.cmdIn;
            connect b.pos to c.posIn;
          }}
        }}
        """,
    )

    return root


def write_sync_pair_architecture(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)

    write_model(
        root / "ports.sysml",
        """
        package Example {
          port def Signal {
            attribute x: Real;
            attribute y: Real;
          }
        }
        """,
    )

    write_model(
        root / "parts.sysml",
        """
        package Example {
          part def Producer {
            out port outSig : Signal;
          }

          part def Consumer {
            in port inSig : Signal;
          }
        }
        """,
    )

    write_model(
        root / "composition.sysml",
        f"""
        package Example {{
          part def {COMPOSITION_NAME} {{
            part src : Producer;
            part dst : Consumer;
            connect src.outSig to dst.inSig;
          }}
        }}
        """,
    )

    return root


def write_incompatible_port_architecture(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)

    write_model(
        root / "ports.sysml",
        """
        package Example {
          port def Cmd {
            attribute pitch: Real;
            attribute mode: Integer;
          }

          port def Pos {
            attribute x: Real;
            attribute y: Real;
          }
        }
        """,
    )

    write_model(
        root / "parts.sysml",
        """
        package Example {
          part def Source {
            out port pos : Pos;
          }

          part def Sink {
            in port posIn : Pos;
            in port cmdIn : Cmd;
          }
        }
        """,
    )

    write_model(
        root / "composition.sysml",
        f"""
        package Example {{
          part def {COMPOSITION_NAME} {{
            part src : Source;
            part dst : Sink;
            connect src.pos to dst.posIn;
          }}
        }}
        """,
    )

    return root


def _edit_ssd(ssd_path: Path, editor) -> None:
    with SSD(ssd_path, mode="a") as ssd:
        assert ssd.system is not None
        editor(ssd)


def _remove_connections(
    ssd_path: Path,
    *,
    start_element: str,
    start_connector_prefix: str,
    end_element: str,
    end_connector_prefix: str,
) -> None:
    def editor(ssd: SSD) -> None:
        ssd.system.connections = [
            connection
            for connection in ssd.system.connections
            if not (
                connection.start_element == start_element
                and (connection.start_connector or "").startswith(start_connector_prefix)
                and connection.end_element == end_element
                and (connection.end_connector or "").startswith(end_connector_prefix)
            )
        ]

    _edit_ssd(ssd_path, editor)


def _rewrite_connections(ssd_path: Path, rewrite_fn) -> None:
    def editor(ssd: SSD) -> None:
        for connection in ssd.system.connections:
            rewrite_fn(connection)

    _edit_ssd(ssd_path, editor)


def _remove_component(ssd_path: Path, component_name: str) -> None:
    def editor(ssd: SSD) -> None:
        ssd.system.elements = [
            element
            for element in ssd.system.elements
            if not isinstance(element, Component) or element.name != component_name
        ]
        ssd.system.connections = [
            connection
            for connection in ssd.system.connections
            if connection.start_element != component_name and connection.end_element != component_name
        ]

    _edit_ssd(ssd_path, editor)


def _duplicate_component(
    ssd_path: Path,
    *,
    source_component: str,
    new_component: str,
    new_connections: list[Connection],
) -> None:
    def editor(ssd: SSD) -> None:
        template = next(
            element
            for element in ssd.system.elements
            if isinstance(element, Component) and element.name == source_component
        )
        duplicate = deepcopy(template)
        duplicate.name = new_component
        ssd.system.elements.append(duplicate)
        ssd.system.connections.extend(new_connections)

    _edit_ssd(ssd_path, editor)


def test_sync_ssd_connection_changes_are_reflected_in_sysml(tmp_path: Path) -> None:
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


def test_sync_ssd_removes_parts_missing_from_ssd(tmp_path: Path) -> None:
    arch_dir = write_connected_triplet_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(arch_dir, ssd_path, COMPOSITION_NAME)

    _remove_component(ssd_path, "c")

    sync_sysml_from_ssd(arch_dir, ssd_path, COMPOSITION_NAME)

    architecture = SysMLParser(arch_dir).parse()
    system = architecture.get_part(COMPOSITION_NAME)
    assert set(system.parts) == {"a", "b"}
    assert {
        (conn.src_component, conn.src_port, conn.dst_component, conn.dst_port)
        for conn in system.connections
    } == {("a", "cmd", "b", "cmdIn")}


def test_sync_ssd_adds_parts_present_in_ssd(tmp_path: Path) -> None:
    arch_dir = write_connected_triplet_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(arch_dir, ssd_path, COMPOSITION_NAME)

    _duplicate_component(
        ssd_path,
        source_component="c",
        new_component="d",
        new_connections=[
            Connection(
                start_element="b",
                start_connector="pos.x",
                end_element="d",
                end_connector="posIn.x",
            ),
            Connection(
                start_element="b",
                start_connector="pos.y",
                end_element="d",
                end_connector="posIn.y",
            ),
        ],
    )

    sync_sysml_from_ssd(arch_dir, ssd_path, COMPOSITION_NAME)

    architecture = SysMLParser(arch_dir).parse()
    system = architecture.get_part(COMPOSITION_NAME)
    assert set(system.parts) == {"a", "b", "c", "d"}
    assert system.parts["d"].part_name == "C"
    assert {
        (conn.src_component, conn.src_port, conn.dst_component, conn.dst_port)
        for conn in system.connections
    } == {
        ("a", "cmd", "b", "cmdIn"),
        ("b", "pos", "c", "posIn"),
        ("b", "pos", "d", "posIn"),
    }


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

    def rewrite(connection: Connection) -> None:
        if (
            connection.start_element == "src"
            and connection.start_connector == "outSig.x"
            and connection.end_element == "dst"
            and connection.end_connector == "inSig.x"
        ):
            connection.end_connector = "inSig.y"

    _rewrite_connections(ssd_path, rewrite)

    with pytest.raises(ValueError, match="attribute remapping"):
        sync_sysml_from_ssd(arch_dir, ssd_path, COMPOSITION_NAME)


def test_sync_ssd_rejects_unknown_component_in_connection(tmp_path: Path) -> None:
    arch_dir = write_sync_pair_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(arch_dir, ssd_path, COMPOSITION_NAME)

    def rewrite(connection: Connection) -> None:
        if connection.start_element == "src":
            connection.start_element = "ghost"

    _rewrite_connections(ssd_path, rewrite)

    with pytest.raises(ValueError, match="unknown source component"):
        sync_sysml_from_ssd(arch_dir, ssd_path, COMPOSITION_NAME)


def test_sync_ssd_rejects_unknown_port(tmp_path: Path) -> None:
    arch_dir = write_sync_pair_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(arch_dir, ssd_path, COMPOSITION_NAME)

    def rewrite(connection: Connection) -> None:
        if connection.end_element == "dst" and connection.end_connector == "inSig.x":
            connection.end_connector = "unknownPort.x"
        if connection.end_element == "dst" and connection.end_connector == "inSig.y":
            connection.end_connector = "unknownPort.y"

    _rewrite_connections(ssd_path, rewrite)

    with pytest.raises(ValueError, match="Unknown destination port"):
        sync_sysml_from_ssd(arch_dir, ssd_path, COMPOSITION_NAME)


def test_sync_ssd_rejects_incompatible_ports(tmp_path: Path) -> None:
    arch_dir = write_incompatible_port_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(arch_dir, ssd_path, COMPOSITION_NAME)

    def rewrite(connection: Connection) -> None:
        if connection.end_element == "dst" and connection.end_connector == "posIn.x":
            connection.end_connector = "cmdIn.x"
        if connection.end_element == "dst" and connection.end_connector == "posIn.y":
            connection.end_connector = "cmdIn.y"

    _rewrite_connections(ssd_path, rewrite)

    with pytest.raises(ValueError, match="incompatible ports"):
        sync_sysml_from_ssd(arch_dir, ssd_path, COMPOSITION_NAME)


def test_sync_ssd_rejects_new_component_with_unknown_source(tmp_path: Path) -> None:
    arch_dir = write_sync_pair_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(arch_dir, ssd_path, COMPOSITION_NAME)

    def editor(ssd: SSD) -> None:
        component = Component()
        component.name = "ghost"
        component.component_type = "application/x-fmu-sharedlibrary"
        component.source = "resources/Unknown.fmu"
        ssd.system.elements.append(component)

    _edit_ssd(ssd_path, editor)

    with pytest.raises(ValueError, match="unknown part source"):
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

    architecture = SysMLParser(out_dir).parse()
    system = architecture.get_part(COMPOSITION_NAME)
    assert system.connections == []
