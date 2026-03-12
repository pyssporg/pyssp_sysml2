from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from pycps_sysmlv2 import SysMLParser
from pyssp_standard.common_content_ssc import TypeReal
from pyssp_standard.ssd import Component, Connection, Connector, SSD, System

from pyssp_sysml2.sysml import generate_sysml_from_ssd
from tests.test_utils import write_bootstrap_ssd


def _architecture_text(path: Path) -> str:
    return str(SysMLParser(path).parse())


def test_generate_sysml_from_ssd_uses_ssd_system_name_by_default(tmp_path: Path) -> None:
    """Generating SysML from SSD writes a minimal single-file architecture."""
    ssd_path = write_bootstrap_ssd(tmp_path / "SystemStructure.ssd")
    output = tmp_path / "generated" / "architecture.sysml"

    written = generate_sysml_from_ssd(ssd_path, output)

    assert written == output
    assert _architecture_text(output) == dedent(
        """
        package RecoveredFromSSD
        part Sink
          port in inSig:Port_1 -> Port_1
        part Source
          port out outSig:Port_1 -> Port_1
        part SystemComposition
          part dst:Sink -> Sink
          part src:Source -> Source
          connect src.outSig -> dst.inSig
        port Port_1
          attr x:Real=None
          attr y:Real=None
        """
    ).strip() + "\n"


def test_generate_sysml_from_ssd_allows_overriding_composition_name(tmp_path: Path) -> None:
    """Generating SysML from SSD can override the top-level composition name."""
    ssd_path = write_bootstrap_ssd(tmp_path / "SystemStructure.ssd")
    output = tmp_path / "architecture.sysml"

    generate_sysml_from_ssd(ssd_path, output, composition="RecoveredComposition")

    assert "part RecoveredComposition" in _architecture_text(output)


def test_generate_sysml_from_ssd_supports_scalar_connectors(tmp_path: Path) -> None:
    """Generating SysML from SSD tolerates scalar connector names without dotted attributes."""
    ssd_path = tmp_path / "scalar.ssd"
    with SSD(ssd_path, mode="w") as ssd:
        ssd.name = "ScalarExample"
        ssd.version = "1.0"
        ssd.system = System(name="ScalarExample")

        src = Component()
        src.name = "src"
        src.source = "resources/Source.fmu"
        src.connectors.append(Connector(name="signal", kind="output", type_=TypeReal(unit=None)))
        ssd.system.elements.append(src)

        dst = Component()
        dst.name = "dst"
        dst.source = "resources/Sink.fmu"
        dst.connectors.append(Connector(name="signal", kind="input", type_=TypeReal(unit=None)))
        ssd.system.elements.append(dst)

        ssd.system.connections.append(
            Connection(
                start_element="src",
                start_connector="signal",
                end_element="dst",
                end_connector="signal",
            )
        )

    output = tmp_path / "scalar.sysml"
    generate_sysml_from_ssd(ssd_path, output)

    assert _architecture_text(output) == dedent(
        """
        package RecoveredFromSSD
        part ScalarExample
          part dst:Sink -> Sink
          part src:Source -> Source
          connect src.signal -> dst.signal
        part Sink
          port in signal:Port_1 -> Port_1
        part Source
          port out signal:Port_1 -> Port_1
        port Port_1
          attr value:Real=None
        """
    ).strip() + "\n"
