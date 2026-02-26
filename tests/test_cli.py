from __future__ import annotations

from pathlib import Path

from pyssp_sysml2.cli import main

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "aircraft_subset"


def test_pyssp_generate_ssd_cli(tmp_path: Path) -> None:
    output = tmp_path / "SystemStructure.ssd"
    code = main(
        [
            "generate",
            "ssd",
            "--architecture",
            str(FIXTURE_DIR),
            "--composition",
            "AircraftComposition",
            "--output",
            str(output),
        ]
    )
    assert code == 0
    assert output.exists()
