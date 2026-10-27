---
id: EVAL-002
type: eval
title: sysmlpy evaluation and recommendation
summary: sysmlpy parses the repository surface and needs thin adapters for port direction, endpoints, and export formatting.
date: 2026-10-14
status: current
---

# sysmlpy evaluation and recommendation

Tested with `sysmlpy==0.96.4` against `examples/aircraft_subset/*.sysml` in a
scratch environment.

## What works

- **Multi-file, same-package merge**: `load_files([...])` merges the aircraft
  files into one package, matching the custom parser's directory mode.
- **Core constructs**: `part def`, `port def` with attributes, `requirement def`
  with `doc`, typed attributes, in and out ports, typed part usages, `connect`,
  doc comments, `specializes`, and `redefines`.
- **Navigation**: `model.packages`, `find_one`, `find(sysml_type="port")`,
  `typed_by_name`, `Attribute.get_value()`, and requirement doc text cover what
  the generators need.
- **Semantic analysis**: `analyze(model)` provides symbol resolution, import
  checking, and well-formedness rules beyond the custom parser.
- **Round-trip export**: `dump()` re-emits valid SysML v2 including doc
  comments, part typings, and `connect` statements.
- **Programmatic construction** plus `dump()` supports the SSD-to-SysML
  direction.
- Dependencies are `pint`, `pyyaml`, and `antlr4-python3-runtime`; `pint` is
  already in the dependency tree through `pyssp_standard`.

## Dialect gaps on our side

Standard SysML v2 rejects three things the old dialect allowed:

1. `attribute comment = "..."`: `comment` is a reserved keyword. Rename the
   attribute.
2. `attribute x = [0.0, 10.0, 20.0];`: bracket lists are not SysML v2. Use a
   tuple.
3. `remove <member>;`: not in SysML v2. It was used only by the submodule's
   inheritance tests and is dropped.

`part def D : B` colon inheritance is also non-standard, but the old parser
already rejected it.

## API gaps needing adapters

- **Port direction** is preserved in the grammar but not surfaced on the public
  `Port` object. Walk the grammar prefix or upstream a direction field.
- **Connection endpoints** parse and round-trip, but the public `Connection`
  object does not expose structured ends. The SSD generator needs source and
  destination part and port tuples.
- **Export formatting** differs from the custom exporter, including spacing and
  per-source-file grouping via `export_declared()`. Tests would be rewritten
  around `dump()` or the JSON interchange format.

## Recommendation

1. Adopt `sysmlpy` as the parsing base behind a thin adapter that reproduces
   load-directory, find part definition, ports with direction, attributes with
   values and types, connections with endpoints, requirements with doc text, and
   model build and export.
2. Fix the dialect first: rename `comment` attributes, use tuple lists, drop
   `remove`.
3. De-scope unused inheritance machinery from the migration; re-add on demand.
4. Mitigate the bus-factor risk. Pin an exact version, vendor it if forkability
   matters, and keep the adapter thin so the parser can be swapped again.
5. If JVM weight is acceptable, the fallback is the official SysML v2 Pilot
   Implementation driven headlessly.

## Migration sketch

1. Fix the dialect in examples and user models.
2. Add a parser-adapter facade over `sysmlpy.load_files`.
3. Port the generators to read from the adapter.
4. Rework export on `dump()` and normalize expected test output.
5. Remove the `pycps_sysmlv2` submodule and its git dependency.
