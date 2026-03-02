from __future__ import annotations

from pathlib import Path

from pyssp_sysml2.cli import main
from pyssp_sysml2.ssd import generate_ssd
from tests.sysml_test_models import COMPOSITION_NAME, write_connected_triplet_architecture


def test_pyssp_generate_ssd_cli(tmp_path: Path) -> None:
    architecture_dir = write_connected_triplet_architecture(tmp_path / "arch")
    output = tmp_path / "SystemStructure.ssd"
    code = main(
        [
            "generate",
            "ssd",
            "--architecture",
            str(architecture_dir),
            "--composition",
            COMPOSITION_NAME,
            "--output",
            str(output),
        ]
    )
    assert code == 0
    assert output.exists()


def test_pyssp_sync_ssd_cli(tmp_path: Path) -> None:
    arch_dir = write_connected_triplet_architecture(tmp_path / "arch")
    ssd_path = tmp_path / "SystemStructure.ssd"
    generate_ssd(arch_dir, ssd_path, COMPOSITION_NAME)

    code = main(
        [
            "sync",
            "ssd",
            "--architecture",
            str(arch_dir),
            "--composition",
            COMPOSITION_NAME,
            "--ssd",
            str(ssd_path),
        ]
    )
    assert code == 0


def test_pyssp_generate_ssd_cli_fails_for_unknown_composition(tmp_path: Path) -> None:
    architecture_dir = write_connected_triplet_architecture(tmp_path / "arch")
    output = tmp_path / "SystemStructure.ssd"
    code = main(
        [
            "generate",
            "ssd",
            "--architecture",
            str(architecture_dir),
            "--composition",
            "MissingComposition",
            "--output",
            str(output),
        ]
    )
    assert code == 1
    assert not output.exists()


def test_pyssp_sync_ssd_cli_fails_for_missing_ssd(tmp_path: Path) -> None:
    arch_dir = write_connected_triplet_architecture(tmp_path / "arch")
    composition_path = arch_dir / "composition.sysml"
    before = composition_path.read_text(encoding="utf-8")
    code = main(
        [
            "sync",
            "ssd",
            "--architecture",
            str(arch_dir),
            "--composition",
            COMPOSITION_NAME,
            "--ssd",
            str(tmp_path / "does_not_exist.ssd"),
        ]
    )
    assert code == 1
    after = composition_path.read_text(encoding="utf-8")
    assert after == before
