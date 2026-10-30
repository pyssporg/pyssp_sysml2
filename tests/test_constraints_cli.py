"""The CLI rejects an illegal variant selection before writing an SSD."""

from __future__ import annotations

from pyssp_sysml2.cli import main
from tests.fixture_files import fixture_text
from tests.testhelpers import write_model


def test_generate_ssd_rejects_illegal_constraint_selection(tmp_path) -> None:
    architecture_dir = tmp_path / "arch"
    write_model(
        architecture_dir / "constraints.sysml",
        fixture_text("constraints/constraints.sysml"),
    )
    output = tmp_path / "SystemStructure.ssd"

    code = main(
        [
            "generate",
            "ssd",
            "--architecture",
            str(architecture_dir),
            "--composition",
            "ConstrainedComposition",
            "--output",
            str(output),
            "--select",
            "source=sineImplementation",
            "--select",
            "gain=twoStage",
        ]
    )

    assert code == 1
    assert not output.exists()
