"""The ``pyssp_flat_connector`` control attribute is read by value.

An absent attribute and ``= false`` both mean per-member connectors; only
``= true`` flattens a port to its port name. The test generates an SSD for each
form and compares connector names and connection endpoints, then reads the same
value back through :func:`flat_connector`.
"""

from __future__ import annotations

from pathlib import Path

from pyssp_standard import SSD

from pyssp_sysml2.artifacts.ssd import flat_connector, generate_ssd
from pyssp_sysml2.model import load
from tests.fixture_files import fixture_text, render_fixture
from tests.testhelpers import COMPOSITION_NAME, write_model

ABSENT = ""
FALSE = "attribute pyssp_flat_connector : Boolean = false;"
TRUE = "attribute pyssp_flat_connector : Boolean = true;"


def _architecture(tmp_path: Path, label: str, setting: str) -> Path:
    root = tmp_path / label
    root.mkdir(parents=True)
    write_model(
        root / "ports.sysml",
        render_fixture("flat-connector/ports.sysml", flat_connector=setting),
    )
    write_model(root / "parts.sysml", fixture_text("flat-connector/parts.sysml"))
    write_model(
        root / "composition.sysml",
        render_fixture(
            "flat-connector/composition.sysml", COMPOSITION_NAME=COMPOSITION_NAME
        ),
    )
    return root


def _ssd_summary(ssd_path: Path) -> dict[str, object]:
    with SSD(ssd_path, mode="r") as ssd:
        assert ssd.system is not None
        connectors = {
            component.name: sorted(
                connector.name for connector in component.connectors
            )
            for component in ssd.system.elements
        }
        connections = sorted(
            (
                connection.start_element,
                connection.start_connector,
                connection.end_element,
                connection.end_connector,
            )
            for connection in ssd.system.connections
        )
    return {"connectors": connectors, "connections": connections}


def _generate(tmp_path: Path, label: str, setting: str) -> dict[str, object]:
    architecture_dir = _architecture(tmp_path / "arch", label, setting)
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(architecture_dir, ssd_path, COMPOSITION_NAME)
    return _ssd_summary(ssd_path)


def _assert_endpoints_are_connectors(summary: dict[str, object]) -> None:
    connectors = summary["connectors"]
    assert isinstance(connectors, dict)
    for start, start_connector, end, end_connector in summary["connections"]:
        assert start_connector in connectors[start]
        assert end_connector in connectors[end]


def test_false_keeps_per_member_connectors_and_true_flattens(tmp_path: Path) -> None:
    """The attribute value, not its presence, decides connector names."""
    absent = _generate(tmp_path / "absent", "absent", ABSENT)
    false = _generate(tmp_path / "false", "false", FALSE)
    true = _generate(tmp_path / "true", "true", TRUE)

    assert false == absent
    assert absent["connectors"] == {"src": ["sig.x"], "dst": ["sigIn.x"]}
    assert absent["connections"] == [("src", "sig.x", "dst", "sigIn.x")]

    assert true["connectors"] == {"src": ["sig"], "dst": ["sigIn"]}
    assert true["connections"] == [("src", "sig", "dst", "sigIn")]

    _assert_endpoints_are_connectors(absent)
    _assert_endpoints_are_connectors(false)
    _assert_endpoints_are_connectors(true)


def test_flat_connector_reads_the_stored_boolean(tmp_path: Path) -> None:
    """Absent and ``false`` report not flattened; ``true`` reports flattened."""
    def _flagged(label: str, setting: str) -> bool:
        architecture_dir = _architecture(tmp_path / label, label, setting)
        architecture = load(architecture_dir)
        return flat_connector(architecture.port_definitions["Signal"])

    assert _flagged("absent", ABSENT) is False
    assert _flagged("false", FALSE) is False
    assert _flagged("true", TRUE) is True
