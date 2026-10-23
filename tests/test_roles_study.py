from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyssp_sysml2.study import generate_study
from pyssp_sysml2.sysml_model import load
from pyssp_sysml2.sysml_model.exporter import export_declared
from pyssp_sysml2.roles import is_ssp_model, is_study


ARCHITECTURE = """\
package RoleModel {
  part def SspModel;
  part def Study;

  port def ParameterInterface;
  attribute def ParameterSet;

  port def LeafParameters :> ParameterInterface {
    attribute k : Real;
  }

  attribute def ScenarioSet :> ParameterSet {
    attribute k = 2.0;
  }

  attribute def Experiment {
    attribute startTime : Real;
    attribute stopTime : Real;
    attribute stepSize : Real;
    attribute tolerance : Real;
  }

  attribute def BaselineExperiment :> Experiment {
    attribute startTime = 0.0;
    attribute stopTime = 1.0;
    attribute stepSize = 0.1;
    attribute tolerance = 0.0001;
  }

  part def Leaf {
    in port parameters : LeafParameters;
  }

  part def System :> SspModel {
    part leaf : Leaf;
  }

  part def test_baseline :> Study {
    attribute experiment_baseline : BaselineExperiment;
    attribute scenario : ScenarioSet;
    part sut : System;
    bind sut.leaf.parameters.k = scenario.k;
  }
}
"""


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


EXPERIMENT_ONLY_ARCHITECTURE = """\
package LegacyStudy {
  part def SspModel;
  part def Study;

  attribute def Experiment {
    attribute startTime : Real;
    attribute stopTime : Real;
    attribute stepSize : Real;
  }

  attribute def BaselineExperiment :> Experiment {
    attribute startTime = 0.0;
    attribute stopTime = 1.0;
    attribute stepSize = 0.001;
  }

  part def LegacyModel :> SspModel;

  part def baseline :> Study {
    attribute experiment_baseline : BaselineExperiment;
    part sut : LegacyModel;
  }
}
"""


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


def test_generate_ssp_rejects_study(tmp_path: Path) -> None:
    from pyssp_sysml2.ssp import generate_ssp

    architecture = _write_architecture(tmp_path)
    with pytest.raises(ValueError, match="Study"):
        generate_ssp(
            architecture,
            tmp_path / "study.ssp",
            "test_baseline",
            validate_fmus=False,
        )
