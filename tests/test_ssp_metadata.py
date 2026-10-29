from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyssp_sysml2.artifacts.ssd import generate_ssd
from pyssp_sysml2.artifacts.ssp import generate_ssp
from pyssp_sysml2.metadata.ssp_metadata import ssp_metadata
from pyssp_sysml2.artifacts.analysis import generate_analysis
from pyssp_sysml2.model import load

from tests.fixture_files import fixture_text


ARCHITECTURE = fixture_text("ssp-metadata/architecture.sysml")


def _architecture(tmp_path: Path, text: str = ARCHITECTURE) -> Path:
    path = tmp_path / "legacy.sysml"
    path.write_text(text, encoding="utf-8")
    return path


def test_generate_analysis_records_model_source(tmp_path: Path) -> None:
    artifacts = generate_analysis(
        _architecture(tmp_path),
        tmp_path / "analysis",
        "baseline",
        model_name="legacy",
    )

    descriptor = json.loads(artifacts.descriptor.read_text(encoding="utf-8"))
    assert descriptor["model_source"] == "models/ssp/example/ssp"
    assert "scenario" not in descriptor
    assert artifacts.ssv is None
    assert artifacts.ssm is None


def test_model_source_is_omitted_when_unset(tmp_path: Path) -> None:
    text = ARCHITECTURE.replace(
        '    attribute source = "models/ssp/example/ssp";\n', ""
    )
    artifacts = generate_analysis(
        _architecture(tmp_path, text),
        tmp_path / "analysis",
        "baseline",
        model_name="legacy",
    )

    descriptor = json.loads(artifacts.descriptor.read_text(encoding="utf-8"))
    assert "model_source" not in descriptor


def test_external_source_is_not_exportable(tmp_path: Path) -> None:
    architecture = _architecture(tmp_path)
    with pytest.raises(ValueError, match="analysis-only boundary"):
        generate_ssp(architecture, tmp_path / "model.ssp", "LegacyBody")
    with pytest.raises(ValueError, match="analysis-only boundary"):
        generate_ssd(architecture, tmp_path / "SystemStructure.ssd", "LegacyBody")


def test_ssp_metadata_requires_an_ssp_model(tmp_path: Path) -> None:
    text = ARCHITECTURE.replace(
        "  part def LegacyBody :> SspModel {\n"
        "    attribute ssp_meta : LegacySsp;\n"
        "  }",
        "  part def PlainPart {\n    attribute ssp_meta : LegacySsp;\n  }",
    )
    architecture = load(_architecture(tmp_path, text))

    with pytest.raises(ValueError, match="not marked ':> SspModel'"):
        ssp_metadata(architecture, architecture.get_part_def("PlainPart"))
