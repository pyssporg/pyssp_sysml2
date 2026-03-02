from __future__ import annotations

import shutil
from pathlib import Path

from pyssp_sysml2.cli import main
from pyssp_sysml2.ssd import generate_ssd

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


def test_pyssp_sync_ssd_cli(tmp_path: Path) -> None:
    arch_dir = tmp_path / "arch"
    shutil.copytree(FIXTURE_DIR, arch_dir)
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(arch_dir, ssd_path, "AircraftComposition")

    code = main(
        [
            "sync",
            "ssd",
            "--architecture",
            str(arch_dir),
            "--composition",
            "AircraftComposition",
            "--ssd",
            str(ssd_path),
        ]
    )
    assert code == 0
