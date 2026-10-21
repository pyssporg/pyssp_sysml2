from __future__ import annotations

from pathlib import Path

import pytest
from pyssp_standard.ssm import SSM
from pyssp_standard.ssv import SSV

from pyssp_sysml2.parameters import (
    mapping_specs,
    parameter_declarations,
    parameter_interface,
)
from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.ssm import generate_parameter_mappings
from pyssp_sysml2.ssv import generate_parameter_sets
from pyssp_sysml2.sysml_model import load
from tests.test_utils import COMPOSITION_NAME, write_model


def _model(
    *,
    interface_marker: str = ":> ParameterInterface",
    interface_members: str = (
        "attribute waypointCount : Integer;\n"
        "    attribute waypointX_km : Real[3];"
    ),
    sets: str = "",
    composition: str = "",
) -> str:
    if not sets:
        sets = """
        attribute def NominalSet :> ParameterSet {
          attribute n_waypoints = 10;
          attribute waypoints_x_km = (0.0, 10.0, 20.0);
        }

        attribute def AggressiveSet :> ParameterSet {
          attribute n_waypoints = 25;
          attribute waypoints_x_km = (0.0, 20.0, 40.0);
        }
        """
    if not composition:
        composition = """
        attribute nominal : NominalSet;
        bind nominal.n_waypoints = autopilot.parameters.waypointCount;
        bind nominal.waypoints_x_km = autopilot.parameters.waypointX_km;
        """
    return f"""
    package Example {{
      attribute def ParameterInterface;
      attribute def ParameterSet;

      attribute def AutopilotParameters {interface_marker} {{
        {interface_members}
      }}

      {sets}

      part def AutopilotModule {{
        attribute parameters : AutopilotParameters;
      }}

      part def {COMPOSITION_NAME} {{
        part autopilot : AutopilotModule;
        {composition}
      }}
    }}
    """


def _write(tmp_path: Path, text: str) -> Path:
    architecture_dir = tmp_path / "arch"
    write_model(architecture_dir / "model.sysml", text)
    return architecture_dir


def _ssv_summary(path: Path) -> list[str]:
    with SSV(path, mode="r") as ssv:
        return sorted(
            f"{parameter.name}:{parameter.type_name}:"
            f"{parameter.attributes.get('value')}"
            for parameter in ssv.xml.parameters
        )


def _ssm_summary(path: Path) -> list[tuple[str, str]]:
    with SSM(path, mode="r") as ssm:
        return [(mapping.source, mapping.target) for mapping in ssm.xml.mappings]


def test_parameter_interface_members_are_declarations(tmp_path) -> None:
    """A typed parameter bag exposes the interface members as declarations."""
    architecture_dir = _write(tmp_path, _model())
    architecture = load(architecture_dir)
    system = architecture.get_part_def(COMPOSITION_NAME)
    part_def = architecture.resolve_part(system.parts["autopilot"])

    assert part_def is not None
    interface = parameter_interface(architecture, part_def)
    assert interface is not None
    assert interface.name == "AutopilotParameters"
    assert [attribute.name for attribute in parameter_declarations(architecture, part_def)] == [
        "waypointCount",
        "waypointX_km",
    ]


def test_generate_ssv_for_applied_set(tmp_path) -> None:
    """The applied set is emitted with its own names, including list indices."""
    architecture_dir = _write(tmp_path, _model())
    output_dir = tmp_path / "sets"

    written = generate_parameter_sets(architecture_dir, output_dir, COMPOSITION_NAME)

    assert [path.name for path in written] == ["NominalSet.ssv"]
    assert _ssv_summary(written[0]) == [
        "n_waypoints:Integer:10",
        "waypoints_x_km[0]:Real:0",
        "waypoints_x_km[1]:Real:10",
        "waypoints_x_km[2]:Real:20",
    ]


def test_generate_ssv_for_all_sets(tmp_path) -> None:
    """--all-sets includes sets that are not applied in the composition."""
    architecture_dir = _write(tmp_path, _model())
    output_dir = tmp_path / "sets"

    written = generate_parameter_sets(
        architecture_dir, output_dir, COMPOSITION_NAME, all_sets=True
    )

    assert [path.name for path in written] == [
        "AggressiveSet.ssv",
        "NominalSet.ssv",
    ]


def test_generate_ssv_single_output_file(tmp_path) -> None:
    """--output works for exactly one selected set and rejects multiple sets."""
    architecture_dir = _write(tmp_path, _model())
    output_path = tmp_path / "custom.ssv"

    written = generate_parameter_sets(
        architecture_dir,
        tmp_path / "unused",
        COMPOSITION_NAME,
        set_names=["NominalSet"],
        output_path=output_path,
    )

    assert written == [output_path]
    assert output_path.exists()

    with pytest.raises(ValueError, match="exactly one parameter set"):
        generate_parameter_sets(
            architecture_dir,
            tmp_path / "unused",
            COMPOSITION_NAME,
            all_sets=True,
            output_path=output_path,
        )


def test_generate_ssm_for_explicit_mapping(tmp_path) -> None:
    """Per-member binds produce source -> hierarchical-target mapping entries."""
    architecture_dir = _write(tmp_path, _model())
    output_dir = tmp_path / "mappings"

    written = generate_parameter_mappings(
        architecture_dir, output_dir, COMPOSITION_NAME
    )

    assert [path.name for path in written] == ["NominalSet_autopilot.ssm"]
    assert _ssm_summary(written[0]) == [
        ("n_waypoints", "autopilot.waypointCount"),
        ("waypoints_x_km[0]", "autopilot.waypointX_km[0]"),
        ("waypoints_x_km[1]", "autopilot.waypointX_km[1]"),
        ("waypoints_x_km[2]", "autopilot.waypointX_km[2]"),
    ]


def test_whole_object_bind_is_identity_and_needs_no_ssm(tmp_path) -> None:
    """A whole-object bind uses matching names and maps to an SSP prefix."""
    model = _model(
        interface_members=(
            "attribute waypointCount : Integer;\n"
            "    attribute waypointX_km : Real[3];"
        ),
        sets="""
        attribute def NominalSet :> ParameterSet {
          attribute waypointCount = 10;
          attribute waypointX_km = (0.0, 10.0, 20.0);
        }
        """,
        composition="""
        attribute nominal : NominalSet;
        bind nominal = autopilot.parameters;
        """,
    )
    architecture_dir = _write(tmp_path, model)
    architecture = load(architecture_dir)
    system = architecture.get_part_def(COMPOSITION_NAME)

    specs = mapping_specs(architecture, system)
    assert len(specs) == 1
    assert specs[0].identity is True
    assert specs[0].entries == (
        ("waypointCount", "autopilot.waypointCount"),
        ("waypointX_km[0]", "autopilot.waypointX_km[0]"),
        ("waypointX_km[1]", "autopilot.waypointX_km[1]"),
        ("waypointX_km[2]", "autopilot.waypointX_km[2]"),
    )

    assert generate_parameter_mappings(
        architecture_dir, tmp_path / "mappings", COMPOSITION_NAME
    ) == []


def test_generate_ssd_rejects_parameter_sets_until_supported(tmp_path) -> None:
    """SSD/FMI generation fails fast instead of emitting bogus parameters."""
    architecture_dir = _write(tmp_path, _model())

    with pytest.raises(ValueError, match="does not support parameter interfaces"):
        generate_ssd(
            architecture_dir, tmp_path / "SystemStructure.ssd", COMPOSITION_NAME
        )


def test_whole_object_bind_requires_matching_names(tmp_path) -> None:
    """Identity bindings cannot absorb differently named set members."""
    model = _model(
        composition="""
        attribute nominal : NominalSet;
        bind nominal = autopilot.parameters;
        """,
    )
    architecture_dir = _write(tmp_path, model)

    with pytest.raises(ValueError, match="cannot map set members"):
        generate_parameter_sets(
            architecture_dir, tmp_path / "sets", COMPOSITION_NAME
        )


def test_unbounded_parameter_multiplicity_is_rejected(tmp_path) -> None:
    """SSP parameters need a fixed length; '[0..*]' is rejected."""
    model = _model(
        interface_members="attribute waypointX_km : Real[0..*];",
        sets="""
        attribute def NominalSet :> ParameterSet {
          attribute waypoints_x_km = (0.0, 10.0);
        }
        """,
        composition="""
        attribute nominal : NominalSet;
        bind nominal.waypoints_x_km = autopilot.parameters.waypointX_km;
        """,
    )
    architecture_dir = _write(tmp_path, model)

    with pytest.raises(ValueError, match="unbounded multiplicity"):
        generate_parameter_sets(
            architecture_dir, tmp_path / "sets", COMPOSITION_NAME
        )


def test_multiple_sets_for_one_component_is_rejected(tmp_path) -> None:
    """Only the effective set is supported; a second application is an error."""
    model = _model(
        composition="""
        attribute nominal : NominalSet;
        attribute aggressive : AggressiveSet;
        bind nominal.n_waypoints = autopilot.parameters.waypointCount;
        bind aggressive.n_waypoints = autopilot.parameters.waypointCount;
        """,
    )
    architecture_dir = _write(tmp_path, model)

    with pytest.raises(ValueError, match="Multiple parameter sets"):
        generate_parameter_sets(
            architecture_dir, tmp_path / "sets", COMPOSITION_NAME
        )


def test_missing_marker_definitions_are_rejected(tmp_path) -> None:
    """The marker defs themselves must exist in the package."""
    model = _model().replace("attribute def ParameterInterface;\n", "").replace(
        "attribute def ParameterSet;\n", ""
    )
    architecture_dir = _write(tmp_path, model)

    with pytest.raises(ValueError, match="missing marker definition"):
        generate_parameter_sets(
            architecture_dir, tmp_path / "sets", COMPOSITION_NAME
        )


def test_unmarked_interface_is_rejected(tmp_path) -> None:
    """A parameters bag typed by an unmarked attribute def fails validation."""
    architecture_dir = _write(tmp_path, _model(interface_marker=""))

    with pytest.raises(ValueError, match="not marked ':> ParameterInterface'"):
        generate_parameter_sets(
            architecture_dir, tmp_path / "sets", COMPOSITION_NAME
        )


def test_unmarked_set_is_rejected(tmp_path) -> None:
    """A set usage must be typed by a def marked ':> ParameterSet'."""
    model = _model(
        sets="""
        attribute def NominalSet {
          attribute n_waypoints = 10;
          attribute waypoints_x_km = (0.0, 10.0, 20.0);
        }
        """,
    )
    architecture_dir = _write(tmp_path, model)

    with pytest.raises(ValueError, match="not marked ':> ParameterSet'"):
        generate_parameter_sets(
            architecture_dir, tmp_path / "sets", COMPOSITION_NAME
        )


def test_mixed_parameter_dialects_are_rejected(tmp_path) -> None:
    """A composition cannot mix a parameter bag with legacy flat attributes."""
    model = _model(
        composition="""
        attribute nominal : NominalSet;
        bind nominal.n_waypoints = autopilot.parameters.waypointCount;
        bind nominal.waypoints_x_km = autopilot.parameters.waypointX_km;
        """,
    )
    # Add a second component that still uses the legacy flat dialect.
    model = model.replace(
        f"part autopilot : AutopilotModule;",
        f"""
        part autopilot : AutopilotModule;
        part legacy : LegacyModule;
        """,
    ).replace(
        "part def AutopilotModule {",
        """
        part def LegacyModule {
          attribute gain = 1.0;
        }

        part def AutopilotModule {""",
    )
    architecture_dir = _write(tmp_path, model)

    with pytest.raises(ValueError, match="mixes parameter interfaces"):
        generate_parameter_sets(
            architecture_dir, tmp_path / "sets", COMPOSITION_NAME
        )


def test_type_mismatch_is_rejected(tmp_path) -> None:
    """Mapping an Integer set member to a Real parameter is an error."""
    model = _model(
        interface_members="attribute waypointCount : Real;",
        sets="""
        attribute def NominalSet :> ParameterSet {
          attribute n_waypoints = 10;
        }
        """,
        composition="""
        attribute nominal : NominalSet;
        bind nominal.n_waypoints = autopilot.parameters.waypointCount;
        """,
    )
    architecture_dir = _write(tmp_path, model)

    with pytest.raises(ValueError, match="incompatible types"):
        generate_parameter_sets(
            architecture_dir, tmp_path / "sets", COMPOSITION_NAME
        )


def test_list_length_mismatch_is_rejected(tmp_path) -> None:
    """A set must provide exactly the number of values the interface declares."""
    model = _model(
        interface_members="attribute waypointX_km : Real[3];",
        sets="""
        attribute def NominalSet :> ParameterSet {
          attribute waypoints_x_km = (0.0, 10.0);
        }
        """,
        composition="""
        attribute nominal : NominalSet;
        bind nominal.waypoints_x_km = autopilot.parameters.waypointX_km;
        """,
    )
    architecture_dir = _write(tmp_path, model)

    with pytest.raises(ValueError, match="provides 2 values"):
        generate_parameter_sets(
            architecture_dir, tmp_path / "sets", COMPOSITION_NAME
        )


def test_unbound_set_member_warns(tmp_path) -> None:
    """A valued set member without a bind is reported but does not fail."""
    model = _model(
        sets="""
        attribute def NominalSet :> ParameterSet {
          attribute n_waypoints = 10;
          attribute waypoints_x_km = (0.0, 10.0, 20.0);
          attribute unused = 1;
        }
        """,
    )
    architecture_dir = _write(tmp_path, model)

    with pytest.warns(UserWarning, match="not bound"):
        generate_parameter_sets(
            architecture_dir, tmp_path / "sets", COMPOSITION_NAME
        )
