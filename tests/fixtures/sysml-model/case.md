# Case: `sysml-model`

Input documents for `tests/test_sysml_model.py`. Every file is a complete SysML
v2 package that a test writes with `write_model` and loads through
`pyssp_sysml2.model.load`; nothing here is an expected artifact.

- **Conversion:** SysML v2 text → `Architecture`, and `Architecture` →
  SysML text through `export_declared()`, which the round-trip case reloads.
- **Requirement / fault:** the loader must keep what the document says and
  merge what the directory says. The set pins single-file loading, sorted
  non-recursive directory merge, package-name mismatch, duplicate part
  definitions, value normalization, string escapes, negative literals, unit
  magnitudes, port directions, docs and requirement text, definition
  specialization, multiplicity, bindings, connection keys and legacy names,
  duplicate-connect collapse, boundary endpoints, syntax-error propagation, and
  the export round trip.
- **Level:** unit, with one contract case (`round-trip.sysml`) where load and
  export must agree.
- **Input:** the files listed below, authored here for these tests; no external
  source and no licence obligation. The multi-file cases keep one file per
  document the test writes, so `merge-a.sysml`, `merge-b.sysml`, and
  `merge-nested/c.sysml` mirror the `a.sysml`, `b.sysml`, and `nested/c.sysml`
  files the merge test creates.
- **Expected:** none. There is no expected output file; each test is its own
  oracle and asserts the loaded dataclasses inline.
- **Independent oracle:** the tests. `tests/test_sysml_model.py` holds the only
  statement of what each document must load into; the round-trip case compares
  the architecture with itself after export, which is the contract under test.
- **Comparison:** exact attribute values, exact key and name lists, and an
  equality check of the flattened architecture summary for the round trip.
- **Normalization:** none. Each file is stored exactly as `write_model` writes
  it: stripped, with one trailing newline. `escapes.sysml` keeps its backslashes
  literal, so the escapes are decoded by the loader, not by Python.
- **Volatile fields:** none.
- **Update policy:** edit a document only together with the test that reads it;
  changing bytes without changing the assertions is the regression the tests
  catch.
- **Notes:** three tests write a file called `values.sysml` in their own tmp
  directory; here they are `values.sysml`, `definition-specialization.sysml`,
  and `attribute-multiplicity.sysml`, because one directory cannot hold three
  files with the same name.

## Artifacts

Inputs, relative to this directory. None is generated.

| Path | Behaviour |
| --- | --- |
| `single.sysml` | single-file load, definitions track their source file |
| `merge-a.sysml` | directory merge: first file, loaded in sorted order |
| `merge-b.sysml` | directory merge: second file |
| `merge-nested/c.sysml` | nested file the non-recursive glob must ignore |
| `package-mismatch-a.sysml` | package `One` |
| `package-mismatch-b.sysml` | package `Two`; mismatch is an error |
| `duplicate-a.sysml` | part def `Dup` in the first file |
| `duplicate-b.sysml` | the same part def name again; duplicate is an error |
| `values.sysml` | attribute value normalization: float, int, string, bool, tuple, declared |
| `escapes.sysml` | string literals with `\n`, `\\`, and `\"` escapes |
| `negative.sysml` | negative real and integer literals keep their sign |
| `units.sysml` | unit literal loads as its bare magnitude |
| `directions.sysml` | in, out, inout, and undirected ports |
| `doc.sysml` | part def doc comment |
| `portdef.sysml` | port def doc and ordered attributes |
| `requirement.sysml` | requirement def text |
| `definition-specialization.sysml` | port and attribute defs keep specialization and members |
| `attribute-multiplicity.sysml` | fixed, bounded, unbounded, and scalar multiplicity |
| `bindings.sysml` | per-member and whole-object binds keep both feature chains |
| `connections.sysml` | connect and explicit connection, keys and legacy names |
| `overwrite.sysml` | identical connects collapse to one entry |
| `multi-a.sysml` | first file of a directory merge with connections |
| `multi-b.sysml` | second file; both files' connections survive |
| `boundary.sysml` | bare connection ends name ports of the enclosing part def |
| `broken.sysml` | a document that does not parse; the error propagates |
| `round-trip.sysml` | load → export → load yields the same architecture |

## What this case proves

Without these documents the loader tests would carry SysML in Python literals,
where a reviewer reads escaped strings instead of model text. Keeping one file
per document also keeps the negative cases honest: a mismatch, a duplicate, or a
syntax error needs its own bytes and cannot share a file with a passing case.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-28 | Case record added; documents moved out of the test module | Test inputs were Python string literals, not reviewable SysML files |
