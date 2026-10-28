from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from pyssp_standard import SSD, SSP

from pyssp_sysml2.cli import _parse_selections, main
from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.ssp import generate_ssp
from pyssp_sysml2.sync import sync_sysml_from_ssd
from pyssp_sysml2.sysml import generate_sysml_from_ssd
from pyssp_sysml2.sysml_model import load
from pyssp_sysml2.variation import has_variation, resolve
from tests.test_utils import write_bootstrap_ssd, write_model


DEFINITION_VARIATION = """\
package DefinitionVariation {
  part def SspModel;
  port def RealSignal {
    attribute pyssp_flat_connector : Boolean = true;
    attribute value : Real;
  }

  part def Step {
    out port y : RealSignal;
  }

  part def Sine {
    out port y : RealSignal;
  }

  part def Gain {
    in port u : RealSignal;
    out port y : RealSignal;
  }

  variation part def SourceChoice {
    variant part stepImplementation : Step;
    variant part sineImplementation : Sine;
  }

  part def System :> SspModel {
    part source : SourceChoice;
    part gain : Gain;
    connect source.y to gain.u;
  }
}
"""

DEFINITION_VARIATION_FMU = """\
package DefinitionVariationFmu {
  part def SspModel;
  port def RealSignal {
    attribute pyssp_flat_connector : Boolean = true;
    attribute value : Real;
  }

  attribute def FmuMetadata {
    attribute source : String;
    attribute implementation : String;
  }

  attribute def StepFmu :> FmuMetadata {
    attribute source = "models/fmu/Step";
    attribute implementation = "CoSimulation";
  }

  attribute def SineFmu :> FmuMetadata {
    attribute source = "models/fmu/Sine";
    attribute implementation = "CoSimulation";
  }

  part def Step {
    attribute fmu_meta : StepFmu;
    out port y : RealSignal;
  }

  part def Sine {
    attribute fmu_meta : SineFmu;
    out port y : RealSignal;
  }

  part def Gain {
    in port u : RealSignal;
    out port y : RealSignal;
  }

  variation part def SourceChoice {
    variant part stepImplementation : Step;
    variant part sineImplementation : Sine;
  }

  part def System :> SspModel {
    part source : SourceChoice;
    part gain : Gain;
    connect source.y to gain.u;
  }
}
"""

USAGE_VARIATION = """\
package UsageVariation {
  part def SspModel;

  part def SignalSource;
  part def Step :> SignalSource;
  part def Sine :> SignalSource;

  part def System :> SspModel {
    variation part source : SignalSource {
      variant part stepSource : Step;
      variant part sineSource : Sine;
    }
  }
}
"""

BODY_VARIATION = """\
package BodyVariation {
  part def SspModel;
  port def RealSignal {
    attribute pyssp_flat_connector : Boolean = true;
    attribute value : Real;
  }

  part def Gain {
    in port u : RealSignal;
    out port y : RealSignal;
  }

  variation part def PathChoice {
    in port u : RealSignal;
    out port y : RealSignal;

    variant part directPath {
      part gain : Gain;
      connect u to gain.u;
      connect gain.y to y;
    }
  }

  part def System :> SspModel {
    part path : PathChoice;
  }
}
"""

NESTED_VARIATION = """\
package NestedVariation {
  part def SspModel;
  part def A;
  part def B;

  variation part def Choice {
    variant part a : A;
    variant part b : B;
  }

  part def Inner {
    part source : Choice;
  }

  part def System :> SspModel {
    part inner : Inner;
  }
}
"""

AMBIGUOUS_NAMES = """\
package AmbiguousNames {
  part def SspModel;
  part def Leaf;

  part def Nested {
    part x : Leaf;
  }

  part def System :> SspModel {
    part x : Leaf;
    part inner : Nested;
  }
}
"""

NO_VARIATION = """\
package NoVariation {
  part def SspModel;
  port def RealSignal {
    attribute pyssp_flat_connector : Boolean = true;
    attribute value : Real;
  }

  part def Step {
    out port y : RealSignal;
  }

  part def Gain {
    in port u : RealSignal;
    out port y : RealSignal;
  }

  part def System :> SspModel {
    part step : Step;
    part gain : Gain;
    connect step.y to gain.u;
  }
}
"""


def _load_architecture(tmp_path: Path, content: str):
    path = tmp_path / "architecture.sysml"
    write_model(path, content)
    return path, load(path)


def test_definition_variation_captures_variants(tmp_path: Path) -> None:
    """A variation definition keeps its flag and its variant members, not parts."""
    _, architecture = _load_architecture(tmp_path, DEFINITION_VARIATION)

    source_choice = architecture.part_definitions["SourceChoice"]
    assert source_choice.is_variation is True
    assert [
        (variant.name, variant.kind, variant.type_name)
        for variant in source_choice.variants
    ] == [
        ("stepImplementation", "part", "Step"),
        ("sineImplementation", "part", "Sine"),
    ]
    assert source_choice.parts == {}


def test_usage_level_variation_is_flagged(tmp_path: Path) -> None:
    """A ``variation part`` usage keeps its flag; its alternatives stay nested."""
    _, architecture = _load_architecture(tmp_path, USAGE_VARIATION)

    system = architecture.part_definitions["System"]
    assert system.is_variation is False
    assert system.parts["source"].is_variation is True
    assert system.variants == []


def test_model_without_variation_stays_clean(tmp_path: Path) -> None:
    """An architecture with no variation construct reports no variation."""
    _, architecture = _load_architecture(tmp_path, NO_VARIATION)

    for definition in architecture.part_definitions.values():
        assert definition.is_variation is False
        assert definition.variants == []
        assert not any(usage.is_variation for usage in definition.parts.values())


def test_generate_ssd_rejects_unresolved_variation(tmp_path: Path) -> None:
    """Generation fails on the variation point, not on the missing ports."""
    path, _ = _load_architecture(tmp_path, DEFINITION_VARIATION)

    with pytest.raises(
        ValueError,
        match="'SourceChoice' in composition 'System' is not resolved.*"
        "not supported yet",
    ):
        generate_ssd(path, tmp_path / "out" / "SystemStructure.ssd", "System")


def test_generate_ssd_still_succeeds_without_variation(tmp_path: Path) -> None:
    """The new check stays inert for a composition without variation."""
    path, _ = _load_architecture(tmp_path, NO_VARIATION)

    output = generate_ssd(path, tmp_path / "out" / "SystemStructure.ssd", "System")
    assert output.exists()


def test_variant_member_with_a_body_loads(tmp_path: Path) -> None:
    """A variant with a body is captured and does not crash the load."""
    _, architecture = _load_architecture(tmp_path, BODY_VARIATION)

    path_choice = architecture.part_definitions["PathChoice"]
    assert path_choice.is_variation is True
    assert [(variant.name, variant.type_name) for variant in path_choice.variants] == [
        ("directPath", None)
    ]
    assert path_choice.parts == {}


def _component_sources(output: Path) -> dict[str, str]:
    with SSD(output, mode="r") as ssd:
        assert ssd.system is not None
        return {element.name: element.source for element in ssd.system.elements}


def test_resolve_substitutes_the_selected_variant(tmp_path: Path) -> None:
    """Resolution rewrites the usage type on a copy and keeps the usage name."""
    _, architecture = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)

    resolved = resolve(architecture, "System", {"source": "stepImplementation"})

    assert resolved.part_definitions["System"].parts["source"].type_name == "Step"
    assert architecture.part_definitions["System"].parts["source"].type_name == (
        "SourceChoice"
    )
    assert list(resolved.part_definitions["System"].parts) == ["source", "gain"]


def test_generate_ssd_selects_step_fmu(tmp_path: Path) -> None:
    """The selected Step variant supplies the component source, name unchanged."""
    path, _ = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)

    output = generate_ssd(
        path,
        tmp_path / "out" / "SystemStructure.ssd",
        "System",
        selections={"source": "stepImplementation"},
    )

    sources = _component_sources(output)
    assert sources["source"] == "resources/Step.fmu"


def test_generate_ssd_selects_sine_fmu(tmp_path: Path) -> None:
    """The other variant changes the source but not the SSD component name."""
    path, _ = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)

    output = generate_ssd(
        path,
        tmp_path / "out" / "SystemStructure.ssd",
        "System",
        selections={"source": "sineImplementation"},
    )

    sources = _component_sources(output)
    assert sources["source"] == "resources/Sine.fmu"


def test_generate_ssp_uses_the_selected_variant(tmp_path: Path) -> None:
    """SSP packaging resolves the selection before building its SSD."""
    path, _ = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)

    with pytest.warns(UserWarning, match="FMU source is missing"):
        output = generate_ssp(
            path,
            tmp_path / "out" / "System.ssp",
            "System",
            allow_missing_fmus=True,
            selections={"source": "sineImplementation"},
        )

    with SSP(output, mode="r") as ssp:
        with ssp.system_structure() as ssd:
            assert ssd.system is not None
            sources = {element.name: element.source for element in ssd.system.elements}
    assert sources["source"] == "resources/Sine.fmu"


def test_resolve_rejects_an_unknown_key(tmp_path: Path) -> None:
    _, architecture = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)

    with pytest.raises(ValueError, match="Unknown selection key 'missing'"):
        resolve(architecture, "System", {"missing": "stepImplementation"})


def test_resolve_accepts_a_dotted_path_for_nesting(tmp_path: Path) -> None:
    """A nested variation point is selected by its dotted usage path."""
    _, architecture = _load_architecture(tmp_path, NESTED_VARIATION)

    resolved = resolve(architecture, "System", {"inner.source": "a"})

    assert resolved.part_definitions["Inner"].parts["source"].type_name == "A"


def test_resolve_rejects_an_ambiguous_bare_key(tmp_path: Path) -> None:
    _, architecture = _load_architecture(tmp_path, AMBIGUOUS_NAMES)

    with pytest.raises(
        ValueError,
        match="Selection key 'x' is ambiguous.*'x', 'inner.x'",
    ):
        resolve(architecture, "System", {"x": "anything"})


def test_resolve_rejects_a_non_variation_usage(tmp_path: Path) -> None:
    _, architecture = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)

    with pytest.raises(
        ValueError,
        match="'gain', which is not a variation point",
    ):
        resolve(architecture, "System", {"gain": "stepImplementation"})


def test_resolve_rejects_an_unknown_variant(tmp_path: Path) -> None:
    _, architecture = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)

    with pytest.raises(
        ValueError,
        match="Unknown variant 'nope' for variation point 'SourceChoice'",
    ):
        resolve(architecture, "System", {"source": "nope"})


def test_resolve_rejects_an_unselected_variation_point(tmp_path: Path) -> None:
    _, architecture = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)

    with pytest.raises(
        ValueError,
        match="Variation point 'SourceChoice' at 'source'.*is not selected",
    ):
        resolve(architecture, "System", {})


def test_resolve_rejects_usage_level_variation(tmp_path: Path) -> None:
    _, architecture = _load_architecture(tmp_path, USAGE_VARIATION)

    with pytest.raises(ValueError, match="usage-level variation is not supported"):
        resolve(architecture, "System", {"source": "stepSource"})


def test_resolve_rejects_a_body_variant(tmp_path: Path) -> None:
    _, architecture = _load_architecture(tmp_path, BODY_VARIATION)

    with pytest.raises(
        ValueError,
        match="'directPath' of variation point 'PathChoice' has no resolvable type",
    ):
        resolve(architecture, "System", {"path": "directPath"})


def test_parse_selections_rejects_a_malformed_value() -> None:
    with pytest.raises(ValueError, match="expected KEY=VARIANT"):
        _parse_selections(["source"])


def test_cli_generate_ssd_selects_a_variant(tmp_path: Path) -> None:
    """`pyssp generate ssd --select source=...` writes the selected variant."""
    path, _ = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)
    output = tmp_path / "out" / "SystemStructure.ssd"

    code = main(
        [
            "generate",
            "ssd",
            "--architecture",
            str(path),
            "--composition",
            "System",
            "--output",
            str(output),
            "--select",
            "source=stepImplementation",
        ]
    )

    assert code == 0
    assert _component_sources(output)["source"] == "resources/Step.fmu"


def test_cli_generate_ssd_reports_a_malformed_selection(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path, _ = _load_architecture(tmp_path, DEFINITION_VARIATION_FMU)

    code = main(
        [
            "generate",
            "ssd",
            "--architecture",
            str(path),
            "--composition",
            "System",
            "--select",
            "source",
        ]
    )

    assert code == 1
    assert "[error] Invalid --select value 'source'" in capsys.readouterr().out


ATTRIBUTE_VARIATION = """\
package AttributeVariation {
  part def SspModel;
  variation attribute def Scale;

  part def System :> SspModel {
    attribute gain : Scale;
  }
}
"""


def test_has_variation_covers_definitions_usages_and_attributes(
    tmp_path: Path,
) -> None:
    _, definition = _load_architecture(tmp_path / "definition", DEFINITION_VARIATION)
    _, usage = _load_architecture(tmp_path / "usage", USAGE_VARIATION)
    _, attribute = _load_architecture(tmp_path / "attribute", ATTRIBUTE_VARIATION)
    _, clean = _load_architecture(tmp_path / "clean", NO_VARIATION)

    assert has_variation(definition) is True
    assert has_variation(usage) is True
    assert has_variation(attribute) is True
    assert has_variation(clean) is False


def test_generate_ssp_records_selection_deterministically(tmp_path: Path) -> None:
    """A selected build carries a byte-stable selection record in extra/."""
    path, _ = _load_architecture(tmp_path, DEFINITION_VARIATION)

    first = generate_ssp(
        path,
        tmp_path / "one.ssp",
        "System",
        selections={"source": "stepImplementation"},
    )
    second = generate_ssp(
        path,
        tmp_path / "two.ssp",
        "System",
        selections={"source": "stepImplementation"},
    )

    with zipfile.ZipFile(first) as archive:
        assert json.loads(
            archive.read("extra/org.pyssp/selection.json")
        ) == {
            "composition": "System",
            "selections": {"source": "stepImplementation"},
        }
    assert first.read_bytes() == second.read_bytes()


def test_generate_ssp_without_selection_adds_no_provenance(
    tmp_path: Path,
) -> None:
    path, _ = _load_architecture(tmp_path, NO_VARIATION)

    output = generate_ssp(path, tmp_path / "plain.ssp", "System")

    with zipfile.ZipFile(output) as archive:
        assert not [
            name for name in archive.namelist() if name.startswith("extra/")
        ]


def test_generate_sysml_refuses_to_overwrite_variation(tmp_path: Path) -> None:
    target = tmp_path / "authored.sysml"
    write_model(target, DEFINITION_VARIATION)
    ssd_path = write_bootstrap_ssd(tmp_path / "in.ssd", "System")

    with pytest.raises(
        ValueError,
        match="SysML export does not represent variation points.*SourceChoice",
    ):
        generate_sysml_from_ssd(ssd_path, target)

    assert "variation part def SourceChoice" in target.read_text()


def test_sync_refuses_to_rewrite_variation(tmp_path: Path) -> None:
    path, _ = _load_architecture(tmp_path / "arch", DEFINITION_VARIATION)
    ssd_path = write_bootstrap_ssd(tmp_path / "in.ssd", "System")

    with pytest.raises(
        ValueError,
        match="SysML export does not represent variation points.*SourceChoice",
    ):
        sync_sysml_from_ssd(path, ssd_path, "System")
