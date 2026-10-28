from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyssp_sysml2.artifacts.study import generate_study
from pyssp_sysml2.model import load
from pyssp_sysml2.model.exporter import export_declared
from pyssp_sysml2.metadata.roles import is_ssp_model, is_study
from tests.fixture_files import fixture_text


ARCHITECTURE = fixture_text("roles-study/architecture.sysml")


def _write_architecture(tmp_path: Path) -> Path:
    path = tmp_path / "architecture.sysml"
    path.write_text(ARCHITECTURE, encoding="utf-8")
    return path


def test_part_definition_specialization_roundtrips(tmp_path: Path) -> None:
    path = _write_architecture(tmp_path)
    architecture = load(path)

    assert architecture.get_part_def("System").specializes == ("SspModel",)
    assert architecture.get_part_def("test_baseline").specializes == ("Study",)
    assert is_ssp_model(architecture, architecture.get_part_def("System"))
    assert is_study(architecture, architecture.get_part_def("test_baseline"))

    exported = export_declared(architecture)["architecture.sysml"]
    assert "part def System :> SspModel {" in exported
    assert "part def test_baseline :> Study {" in exported

    roundtrip = tmp_path / "roundtrip"
    roundtrip.mkdir()
    (roundtrip / "architecture.sysml").write_text(exported, encoding="utf-8")
    reloaded = load(roundtrip)
    assert reloaded.get_part_def("System").specializes == ("SspModel",)
    assert reloaded.get_part_def("test_baseline").specializes == ("Study",)


def test_generate_study_writes_scenario_and_descriptor(tmp_path: Path) -> None:
    architecture = _write_architecture(tmp_path)
    output = tmp_path / "study"
    artifacts = generate_study(
        architecture,
        output,
        "test_baseline",
        model_name="role_model",
    )

    assert artifacts.ssv.is_file()
    assert artifacts.ssm.is_file()
    assert artifacts.descriptor.is_file()
    assert not any(output.glob("*.ssd"))
    assert not any(output.glob("*.ssp"))

    descriptor = json.loads(artifacts.descriptor.read_text(encoding="utf-8"))
    assert descriptor["study"] == "test_baseline"
    assert descriptor["composition"] == "System"
    assert descriptor["sut"] == "sut"
    assert descriptor["scenario"]["ssv"] == artifacts.ssv.name
    assert descriptor["scenario"]["ssm"] == artifacts.ssm.name

    ssm = artifacts.ssm.read_text(encoding="utf-8")
    assert 'target="leaf.k"' in ssm
    assert 'target="sut.' not in ssm


EXPERIMENT_ONLY_ARCHITECTURE = fixture_text("roles-study/experiment-only.sysml")


def test_generate_study_without_scenario_writes_experiment_only(tmp_path: Path) -> None:
    architecture = tmp_path / "legacy.sysml"
    architecture.write_text(EXPERIMENT_ONLY_ARCHITECTURE, encoding="utf-8")
    output = tmp_path / "study"
    artifacts = generate_study(
        architecture,
        output,
        "baseline",
        model_name="legacy_model",
    )

    assert artifacts.descriptor.is_file()
    assert artifacts.ssv is None
    assert artifacts.ssm is None
    assert artifacts.scenario_set is None
    assert list(output.glob("*.ssv")) == []
    assert list(output.glob("*.ssm")) == []

    descriptor = json.loads(artifacts.descriptor.read_text(encoding="utf-8"))
    assert "scenario" not in descriptor
    assert descriptor["model"] == "legacy_model"
    assert descriptor["composition"] == "LegacyModel"
    assert descriptor["sut"] == "sut"
    assert descriptor["study"] == "baseline"
    assert descriptor["experiment"] == {
        "name": "experiment_baseline",
        "start_time": 0.0,
        "stop_time": 1.0,
        "step_size": 0.001,
    }


def test_generate_study_writes_study_doc_as_description(tmp_path: Path) -> None:
    architecture = tmp_path / "described.sysml"
    architecture.write_text(
        EXPERIMENT_ONLY_ARCHITECTURE.replace(
            "  part def baseline :> Study {",
            "  part def baseline :> Study {\n"
            "    doc /* Baseline body over the default window. */",
        ),
        encoding="utf-8",
    )
    output = tmp_path / "study"
    artifacts = generate_study(
        architecture,
        output,
        "baseline",
        model_name="described_model",
    )

    descriptor = json.loads(artifacts.descriptor.read_text(encoding="utf-8"))
    assert descriptor["description"] == "Baseline body over the default window."


MODEL_OWNED_SCENARIO_ARCHITECTURE = fixture_text(
    "roles-study/model-owned-scenario.sysml"
)


def test_generate_study_with_model_owned_scenario_writes_experiment_only(
    tmp_path: Path,
) -> None:
    architecture = tmp_path / "model_owned.sysml"
    architecture.write_text(MODEL_OWNED_SCENARIO_ARCHITECTURE, encoding="utf-8")
    output = tmp_path / "study"

    artifacts = generate_study(
        architecture,
        output,
        "baseline",
        model_name="model_owned",
    )

    assert artifacts.ssv is None
    assert artifacts.ssm is None
    assert artifacts.scenario_set is None
    descriptor = json.loads(artifacts.descriptor.read_text(encoding="utf-8"))
    assert "scenario" not in descriptor


def test_generate_study_rejects_study_scenario_when_model_owns_one(
    tmp_path: Path,
) -> None:
    architecture = tmp_path / "conflict.sysml"
    architecture.write_text(
        MODEL_OWNED_SCENARIO_ARCHITECTURE.replace(
            """  part def baseline :> Study {
    attribute experiment_baseline : BaselineExperiment;
    part sut : System;
  }""",
            """  part def baseline :> Study {
    attribute experiment_baseline : BaselineExperiment;
    attribute scenario : ScenarioSet;
    part sut : System;
    bind sut.leaf.parameters.k = scenario.k;
  }""",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="already applies one"):
        generate_study(
            architecture,
            tmp_path / "study",
            "baseline",
            model_name="model_owned",
        )


def test_generate_ssd_emits_model_owned_parameter_binding(tmp_path: Path) -> None:
    from pyssp_sysml2.artifacts.ssd import generate_ssd

    architecture = tmp_path / "model_owned.sysml"
    architecture.write_text(MODEL_OWNED_SCENARIO_ARCHITECTURE, encoding="utf-8")
    output = tmp_path / "SystemStructure.ssd"

    generate_ssd(architecture, output, "System")

    text = output.read_text(encoding="utf-8")
    assert 'ParameterBinding source="parameter_sets/ScenarioSet.ssv"' in text
    assert 'MappingEntry source="k" target="leaf.k"' in text


def test_generate_ssp_rejects_study(tmp_path: Path) -> None:
    from pyssp_sysml2.artifacts.ssp import generate_ssp

    architecture = _write_architecture(tmp_path)
    with pytest.raises(ValueError, match="Study"):
        generate_ssp(
            architecture,
            tmp_path / "study.ssp",
            "test_baseline",
            validate_fmus=False,
        )
