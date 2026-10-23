"""Loader tests: sysmlpy → repo-owned model, and the export round trip.

Everything here goes through the public ``pyssp_sysml2.sysml_model`` surface
(``load`` + dataclasses) so the tests stay insulated from sysmlpy, exactly
like the rest of the repo.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyssp_sysml2.sysml_model import Architecture, load
from tests.test_utils import write_model


# -- single-file and directory loading --------------------------------------


def test_load_single_file(tmp_path) -> None:
    """A file path loads exactly that file; definitions track their source."""
    model_file = tmp_path / "model.sysml"
    write_model(
        model_file,
        """
        package Single {
          port def Signal { attribute level : Real; }

          part def Source { out port sig : Signal; }
        }
        """,
    )

    architecture = load(model_file)

    assert isinstance(architecture, Architecture)
    assert architecture.package_name == "Single"
    assert list(architecture.port_definitions) == ["Signal"]
    assert list(architecture.part_definitions) == ["Source"]
    assert architecture.part_definitions["Source"].source_file == "model.sysml"


def test_load_directory_merges_sorted_files(tmp_path) -> None:
    """A directory loads its *.sysml files sorted, non-recursively, merged."""
    architecture_dir = tmp_path / "arch"
    write_model(
        architecture_dir / "a.sysml",
        """
        package Merged {
          part def Zed { attribute z : Real; }
        }
        """,
    )
    write_model(
        architecture_dir / "b.sysml",
        """
        package Merged {
          part def Alpha { attribute a : Real; }
        }
        """,
    )
    # Nested files must be ignored (the glob is non-recursive) ...
    write_model(
        architecture_dir / "nested" / "c.sysml",
        """
        package Merged {
          part def Nested { attribute n : Real; }
        }
        """,
    )
    # ... and non-.sysml files too.
    (architecture_dir / "notes.txt").write_text("not a model\n", encoding="utf-8")

    architecture = load(architecture_dir)

    # Sorted file order (a.sysml before b.sysml), not definition-name order.
    assert list(architecture.part_definitions) == ["Zed", "Alpha"]
    assert "Nested" not in architecture.part_definitions
    assert architecture.part_definitions["Zed"].source_file == "a.sysml"
    assert architecture.part_definitions["Alpha"].source_file == "b.sysml"

    # export_declared groups by the tracked source files.
    exported = architecture.export_declared()
    assert sorted(exported) == ["a.sysml", "b.sysml"]
    assert "part def Zed" in exported["a.sysml"]
    assert "part def Alpha" in exported["b.sysml"]


def test_missing_path_raises_file_not_found(tmp_path) -> None:
    """A missing path raises the FileNotFoundError sync.py bootstraps from."""
    missing = tmp_path / "missing.sysml"

    with pytest.raises(FileNotFoundError) as excinfo:
        load(missing)

    assert str(excinfo.value) == f"No .sysml file found under {missing}"


def test_empty_directory_raises_file_not_found(tmp_path) -> None:
    """A directory without .sysml files raises FileNotFoundError."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    with pytest.raises(FileNotFoundError) as excinfo:
        load(empty_dir)

    assert str(excinfo.value) == f"No .sysml files found under {empty_dir}"


def test_package_mismatch_across_files_raises(tmp_path) -> None:
    """All files must declare the same package; the first file's name wins."""
    architecture_dir = tmp_path / "arch"
    write_model(
        architecture_dir / "a.sysml",
        """
        package One {
          part def A { attribute a : Real; }
        }
        """,
    )
    write_model(
        architecture_dir / "b.sysml",
        """
        package Two {
          part def B { attribute b : Real; }
        }
        """,
    )

    with pytest.raises(ValueError) as excinfo:
        load(architecture_dir)

    assert str(excinfo.value) == (
        f"Mismatched package names: One vs Two in {architecture_dir / 'b.sysml'}"
    )


def test_duplicate_part_definition_across_files_raises(tmp_path) -> None:
    """A part def name reused across files is an error, naming the file."""
    architecture_dir = tmp_path / "arch"
    write_model(
        architecture_dir / "a.sysml",
        """
        package Same {
          part def Dup { attribute a : Real; }
        }
        """,
    )
    write_model(
        architecture_dir / "b.sysml",
        """
        package Same {
          part def Dup { attribute b : Real; }
        }
        """,
    )

    with pytest.raises(ValueError) as excinfo:
        load(architecture_dir)

    assert str(excinfo.value) == (
        f"Duplicate part definition for Dup in {architecture_dir / 'b.sysml'}"
    )


# -- attribute values ---------------------------------------------------------


def test_value_normalization(tmp_path) -> None:
    """Attribute values come back Python-native (legacy §5.5 semantics)."""
    model_file = tmp_path / "values.sysml"
    write_model(
        model_file,
        """
        package Values {
          part def Values {
            attribute f : Real = 1.0;
            attribute i = 42;
            attribute s = "hi";
            attribute t = true;
            attribute f2 = false;
            attribute taps = (1.0, 2.0);
            attribute declared : Real;
          }
        }
        """,
    )

    attributes = load(model_file).part_definitions["Values"].attributes

    assert attributes["f"].value == 1.0
    assert isinstance(attributes["f"].value, float)
    assert attributes["f"].type_name == "Real"

    assert attributes["i"].value == 42
    assert isinstance(attributes["i"].value, int)
    assert attributes["i"].effective_type_name == "Integer"

    assert attributes["s"].value == "hi"

    assert attributes["t"].value is True
    assert attributes["f2"].value is False

    assert attributes["taps"].value == (1.0, 2.0)
    assert attributes["taps"].is_list
    # An untyped tuple infers its element type from the first element.
    assert attributes["taps"].effective_type_name == "Real"

    assert attributes["declared"].value is None
    assert attributes["declared"].type_name == "Real"


def test_negative_scalar_value_keeps_sign(tmp_path) -> None:
    """Negative number literals keep their sign.

    sysmlpy 0.96.4's get_value() drops a leading unary minus (-1.5 reads as
    1.5); the loader re-attaches it from the grammar layer.
    """
    model_file = tmp_path / "negative.sysml"
    write_model(
        model_file,
        """
        package Negative {
          part def Offsets {
            attribute real = -1.5;
            attribute integer = -7;
          }
        }
        """,
    )

    attributes = load(model_file).part_definitions["Offsets"].attributes

    assert attributes["real"].value == -1.5
    assert attributes["integer"].value == -7


def test_pint_quantity_value_uses_magnitude(tmp_path) -> None:
    """Unit literals (pint Quantities) load as their bare magnitude."""
    model_file = tmp_path / "units.sysml"
    write_model(
        model_file,
        """
        package Units {
          part def Physical {
            attribute mass : Real = 1000 [kilogram];
          }
        }
        """,
    )

    attribute = load(model_file).part_definitions["Physical"].attributes["mass"]

    assert attribute.value == 1000
    assert attribute.type_name == "Real"


# -- ports, docs, requirements ------------------------------------------------


def test_port_directions(tmp_path) -> None:
    """Port usages carry in/out/inout; undirected ports stay None."""
    model_file = tmp_path / "directions.sysml"
    write_model(
        model_file,
        """
        package Directions {
          port def Signal { attribute level : Real; }

          part def Directions {
            in port a : Signal;
            out port b : Signal;
            inout port c : Signal;
            port plain : Signal;
          }
        }
        """,
    )

    ports = load(model_file).part_definitions["Directions"].ports

    assert ports["a"].direction == "in"
    assert ports["b"].direction == "out"
    assert ports["c"].direction == "inout"
    assert ports["plain"].direction is None
    assert ports["a"].type_name == "Signal"


def test_part_definition_doc(tmp_path) -> None:
    """A part def's doc comment becomes PartDefinition.doc."""
    model_file = tmp_path / "doc.sysml"
    write_model(
        model_file,
        """
        package Docs {
          part def Documented {
            doc /* Part doc. */
            attribute x : Real;
          }
        }
        """,
    )

    part_def = load(model_file).part_definitions["Documented"]

    assert part_def.doc == "Part doc."
    assert part_def.attributes["x"].value is None


def test_port_definition_attributes(tmp_path) -> None:
    """A port def keeps its doc and its ordered attributes."""
    model_file = tmp_path / "portdef.sysml"
    write_model(
        model_file,
        """
        package PortDefs {
          port def Signal {
            doc /* Signal doc. */
            attribute level : Real;
            attribute count : Integer;
          }
        }
        """,
    )

    port_def = load(model_file).port_definitions["Signal"]

    assert port_def.doc == "Signal doc."
    assert list(port_def.attributes) == ["level", "count"]
    assert port_def.attributes["level"].type_name == "Real"
    assert port_def.attributes["count"].type_name == "Integer"


def test_requirement_definition_text(tmp_path) -> None:
    """A requirement def's doc comment becomes RequirementDefinition.text."""
    model_file = tmp_path / "requirement.sysml"
    write_model(
        model_file,
        """
        package Requirements {
          requirement def Connected {
            doc /* src must connect to dst */
          }
        }
        """,
    )

    requirement = load(model_file).requirement_definitions["Connected"]

    assert requirement.text == "src must connect to dst"


# -- connections ---------------------------------------------------------------


def test_definition_specialization(tmp_path) -> None:
    """Package defs keep members, markers, and source files."""
    model_file = tmp_path / "values.sysml"
    write_model(
        model_file,
        """
        package Values {
          port def ParameterInterface;
          attribute def ParameterSet;

          port def Interface :> ParameterInterface {
            attribute gain : Real;
            attribute count : Integer;
          }

          attribute def NominalSet :> ParameterSet {
            attribute gain_value = 2.0;
          }
        }
        """,
    )

    architecture = load(model_file)

    assert list(architecture.port_definitions) == [
        "ParameterInterface",
        "Interface",
    ]
    assert list(architecture.attribute_definitions) == [
        "ParameterSet",
        "NominalSet",
    ]
    interface = architecture.port_definitions["Interface"]
    assert interface.specializes == ("ParameterInterface",)
    assert interface.source_file == "values.sysml"
    assert list(interface.attributes) == ["gain", "count"]
    assert interface.attributes["gain"].type_name == "Real"

    nominal = architecture.attribute_definitions["NominalSet"]
    assert nominal.specializes == ("ParameterSet",)
    assert nominal.attributes["gain_value"].value == 2.0


def test_attribute_multiplicity(tmp_path) -> None:
    """Declared multiplicities survive loading (fixed, bounded, unbounded)."""
    model_file = tmp_path / "values.sysml"
    write_model(
        model_file,
        """
        package Values {
          part def Multi {
            attribute fixed : Real[3];
            attribute bounded : Integer[2..4];
            attribute unbounded : Real[0..*];
            attribute scalar : Real;
          }
        }
        """,
    )

    attributes = load(model_file).part_definitions["Multi"].attributes

    assert attributes["fixed"].multiplicity == "3"
    assert attributes["bounded"].multiplicity == "2..4"
    assert attributes["unbounded"].multiplicity == "0..*"
    assert attributes["scalar"].multiplicity is None


def test_bindings_loaded_with_feature_chains(tmp_path) -> None:
    """Per-member and whole-object bindings keep both feature chains."""
    model_file = tmp_path / "bindings.sysml"
    write_model(
        model_file,
        """
        package Bindings {
          attribute def Interface {
            attribute gain : Real;
          }

          attribute def Set {
            attribute gain_value = 2.0;
          }

          part def Component {
            in port parameters : Interface;
          }

          part def SystemComposition {
            part componentA : Component;
            part componentB : Component;
            attribute nominal : Set;

            bind componentA.parameters.gain = nominal.gain_value;
            bind componentB.parameters = nominal;
          }
        }
        """,
    )

    bindings = load(model_file).part_definitions["SystemComposition"].bindings

    # Fields are positional: source is the left-hand side (the port), target is
    # the right-hand side (the set usage).
    assert [(binding.source, binding.target) for binding in bindings] == [
        (("componentA", "parameters", "gain"), ("nominal", "gain_value")),
        (("componentB", "parameters"), ("nominal",)),
    ]
    assert all(binding.name is None for binding in bindings)


def test_connections_stored_by_key_with_legacy_names(tmp_path) -> None:
    """Connections are keyed by endpoint pair; names follow the legacy scheme."""
    model_file = tmp_path / "connections.sysml"
    write_model(
        model_file,
        """
        package Connections {
          part def Source {
            out port outSig : Signal;
            out port aux : Signal;
          }

          part def Sink { in port inSig : Signal; }

          part def SystemComposition {
            part src : Source;
            part dst : Sink;
            connect src.outSig to dst.inSig;
            connection explicit : Link connect src.aux to dst.inSig;
          }
        }
        """,
    )

    connections = load(model_file).part_definitions["SystemComposition"].connections

    assert set(connections) == {"src.outSig->dst.inSig", "src.aux->dst.inSig"}

    unnamed = connections["src.outSig->dst.inSig"]
    assert unnamed.name == "src.outSig_to_dst.inSig"
    assert (
        unnamed.source_part,
        unnamed.source_port,
        unnamed.destination_part,
        unnamed.destination_port,
    ) == ("src", "outSig", "dst", "inSig")

    # An explicitly named connection keeps its given name.
    assert connections["src.aux->dst.inSig"].name == "explicit"


def test_identical_connect_overwrites_earlier(tmp_path) -> None:
    """Connects with identical endpoints collapse to one entry (legacy parity)."""
    model_file = tmp_path / "overwrite.sysml"
    write_model(
        model_file,
        """
        package Overwrite {
          part def SystemComposition {
            part src : Source;
            part dst : Sink;
            connect src.outSig to dst.inSig;
            connect src.outSig to dst.inSig;
          }
        }
        """,
    )

    connections = load(model_file).part_definitions["SystemComposition"].connections

    assert list(connections) == ["src.outSig->dst.inSig"]


def test_connections_from_all_files(tmp_path) -> None:
    """A directory merge keeps every file's connections, in file order."""
    architecture_dir = tmp_path / "arch"
    write_model(
        architecture_dir / "a.sysml",
        """
        package Multi {
          part def CompA {
            part a : A;
            part b : B;
            connect a.p to b.q;
          }
        }
        """,
    )
    write_model(
        architecture_dir / "b.sysml",
        """
        package Multi {
          part def CompB {
            part c : C;
            part d : D;
            connect c.r to d.s;
          }
        }
        """,
    )

    architecture = load(architecture_dir)

    assert list(architecture.part_definitions) == ["CompA", "CompB"]
    assert list(architecture.part_definitions["CompA"].connections) == ["a.p->b.q"]
    assert list(architecture.part_definitions["CompB"].connections) == ["c.r->d.s"]


def test_boundary_connection_endpoints_load(tmp_path) -> None:
    """A bare end names a port of the enclosing part def (system boundary)."""
    model_file = tmp_path / "boundary.sysml"
    write_model(
        model_file,
        """
        package Boundary {
          part def Source {
            out port outSig : Signal;
          }

          part def Sink { in port inSig : Signal; }

          part def Inner {
            in port u : Signal;
            out port v : Signal;
            part src : Source;
            part dst : Sink;
            connect u to src.inSig;
            connect src.outSig to dst.inSig;
            connect dst.inSig to v;
          }
        }
        """,
    )

    connections = load(model_file).part_definitions["Inner"].connections

    assert list(connections) == [
        "u->src.inSig",
        "src.outSig->dst.inSig",
        "dst.inSig->v",
    ]
    assert (
        connections["u->src.inSig"].source_part,
        connections["u->src.inSig"].source_port,
        connections["u->src.inSig"].destination_part,
        connections["u->src.inSig"].destination_port,
    ) == (None, "u", "src", "inSig")
    assert connections["u->src.inSig"].name == "u_to_src.inSig"
    assert connections["dst.inSig->v"].destination_part is None


# -- syntax errors --------------------------------------------------------------


def test_syntax_error_propagates(tmp_path) -> None:
    """A syntax error surfaces as an exception from load (message not pinned)."""
    model_file = tmp_path / "broken.sysml"
    write_model(
        model_file,
        """
        package Broken {
          part def A {
            attribute comment = "x";
          }
        }
        """,
    )

    # sysmlpy raises SysMLSyntaxError, a plain Exception subclass; only the
    # propagation is part of the loader contract, not the message.
    with pytest.raises(Exception):  # noqa: B017, BLE001
        load(model_file)


# -- export round trip ------------------------------------------------------------


def _architecture_summary(architecture: Architecture) -> dict:
    """Flat comparable view of an architecture for round-trip assertions.

    Deliberately excludes, with reasons:

    - member-level docs (attribute/port/part/connection ``doc``): sysmlpy
      attaches a ``doc /* ... */`` written above a member to the *owning
      definition*, so member docs cannot survive a text round trip
      (def-level docs and requirement text below prove docs do survive);
    - raw ``attribute.type_name``: the exporter always writes
      ``effective_type_name``, so inferred types materialize as declared
      ones after export — comparing the effective type keeps that stable;
    - connection/binding ``name`` and ``source_file``: unnamed members get
      endpoint-derived names (or None) and the exporter does not re-emit
      explicit names; source files are covered by the directory tests.
    """
    return {
        "package_name": architecture.package_name,
        "port_definitions": {
            port_def.name: {
                "doc": port_def.doc,
                "attributes": {
                    attribute.name: (
                        attribute.effective_type_name,
                        attribute.multiplicity,
                        attribute.value,
                    )
                    for attribute in port_def.attributes.values()
                },
            }
            for port_def in architecture.port_definitions.values()
        },
        "attribute_definitions": {
            attribute_def.name: {
                "doc": attribute_def.doc,
                "specializes": attribute_def.specializes,
                "attributes": {
                    attribute.name: (
                        attribute.effective_type_name,
                        attribute.multiplicity,
                        attribute.value,
                    )
                    for attribute in attribute_def.attributes.values()
                },
            }
            for attribute_def in architecture.attribute_definitions.values()
        },
        "part_definitions": {
            part_def.name: {
                "doc": part_def.doc,
                "attributes": {
                    attribute.name: (
                        attribute.effective_type_name,
                        attribute.multiplicity,
                        attribute.value,
                    )
                    for attribute in part_def.attributes.values()
                },
                "ports": {
                    port.name: (port.direction, port.type_name)
                    for port in part_def.ports.values()
                },
                "parts": {part.name: part.type_name for part in part_def.parts.values()},
                "connections": {
                    connection.key: (
                        connection.source_part,
                        connection.source_port,
                        connection.destination_part,
                        connection.destination_port,
                    )
                    for connection in part_def.connections.values()
                },
                "bindings": [
                    (binding.source, binding.target) for binding in part_def.bindings
                ],
            }
            for part_def in architecture.part_definitions.values()
        },
        "requirement_definitions": {
            requirement.name: requirement.text
            for requirement in architecture.requirement_definitions.values()
        },
    }


def test_export_round_trip(tmp_path) -> None:
    """load → export_declared → load again yields the same architecture."""
    source_dir = tmp_path / "source"
    write_model(
        source_dir / "model.sysml",
        """
        package RoundTrip {
          port def ParameterInterface;
          attribute def ParameterSet;

          port def Measurements :> ParameterInterface {
            attribute temperature : Real[2];
          }

          attribute def NominalMeasurements :> ParameterSet {
            attribute temps = (1.0, 2.0);
          }

          port def Signal {
            doc /* A signal. */
            attribute level : Real;
            attribute count : Integer;
          }

          part def Source {
            doc /* Source doc. */
            attribute gain : Real = 2.0;
            attribute offset = -1.5;
            attribute label = "hi";
            attribute enabled = true;
            attribute taps = (1.0, 2.0);
            out port sig : Signal;
          }

          part def Sink {
            in port sigIn : Signal;
          }

          part def Measured {
            in port parameters : Measurements;
          }

          part def SystemComposition {
            out port outSig : Signal;
            part src : Source;
            part dst : Sink;
            part measured : Measured;
            attribute nominal : NominalMeasurements;

            connect src.sig to dst.sigIn;
            connect src.sig to outSig;
            bind measured.parameters.temperature = nominal.temps;
          }

          requirement def Connected {
            doc /* src must connect to dst */
          }
        }
        """,
    )

    original = load(source_dir)
    exported = original.export_declared()

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    for file_name, text in exported.items():
        (output_dir / file_name).write_text(text, encoding="utf-8")

    reloaded = load(output_dir)

    assert _architecture_summary(reloaded) == _architecture_summary(original)

    # Def-level docs survive the round trip.
    assert reloaded.port_definitions["Signal"].doc == "A signal."
    assert reloaded.part_definitions["Source"].doc == "Source doc."
    assert reloaded.requirement_definitions["Connected"].text == "src must connect to dst"
