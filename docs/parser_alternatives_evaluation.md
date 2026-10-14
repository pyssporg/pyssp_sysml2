# SysML v2 Parser Alternatives — Evaluation

> **Status: adopted.** The recommendation below was executed — `sysmlpy==0.96.4`
> is now the parsing base behind the `pyssp_sysml2.sysml_model` adapter
> (see `docs/development.md`), and the `pycps_sysmlv2` submodule has been
> removed. The dialect fixes (rename `comment` attributes, tuple lists) were
> applied to `examples/aircraft_subset`.

**Date:** 2026-10-14
**Question:** Can the custom `pycps_sysmlv2` parser (regex/line-based subset parser in `3rd_party/pysysml2_cps`) be replaced by a more established open-source alternative?

## TL;DR

**Yes, replacement is feasible, and `sysmlpy` is the strongest candidate** — with an
important caveat about project maturity. The subset of SysML v2 that this project
actually uses is (almost entirely) standard-conformant textual notation, so a
conformant parser can replace the custom one. Two constructs in our own example
models are non-standard and need mechanical fixes, and the submodule's `remove`
statement has no standard equivalent and would be dropped.

## What the replacement must cover

Current usage surface (from `src/pyssp_sysml2/` — `ssd.py`, `ssv.py`, `fmi.py`,
`sysml.py`, `sync.py`):

- Parse a directory of `.sysml` files that all declare the **same package name**
  (merged into one model).
- Walk: `part def` (attributes, typed part usages, in/out ports, `connect`
  statements), `port def` (attributes), `requirement def` (doc text).
- Attribute values (numbers, strings, booleans, lists), types (`Real`,
  `Integer`, `Boolean`, `String`), `doc /* ... */` comments.
- Reverse direction: build a model programmatically and export SysML text
  (`generate sysml`, `sync ssd`).

**Not used anywhere in this repo:** `specializes`, `redefines`, `remove`.
Those live only in the submodule's own test suite (`3rd_party/pysysml2_cps/tests/`)
and its `inheritance.py`/`exporter.py`. The main repo's models and generators
never emit or consume them (verified by grep over `src/`, `tests/`, and
`examples/**/*.sysml`).

## Candidate landscape

| Project | Language | Parser tech | Coverage | Maintenance | Verdict |
|---|---|---|---|---|---|
| **SysML v2 Pilot Implementation** (Systems-Modeling, OMG SST) | Java/Xtext | full reference impl | Complete (defines the standard) | Very active, backed by OMG submission team | Most established, but JVM — heavyweight for a pip-installable CLI; usable via subprocess or the v2 REST API |
| **Eclipse SysON** (Obeo/Eclipse) | Java (Sirius Web) | full | Complete | Active, Eclipse Foundation | Web platform, not an embeddable Python library |
| **sysml-2ls / SysIDE** (Sensmetry) | TypeScript | full (2024-12 spec) | Good | Active company, MIT | LSP/VS Code tooling; wrong shape for a generator library |
| **sysmlpy** (mycr0ft) | Python | ANTLR4, grammar from `daltskin/sysml-v2-grammar` (tracks OMG releases; vendored 2026-08) | **123/123 OMG XPect conformance**, 168/168 round-trip tests, 1635 tests total | Very active through 2026 (v0.96.4, Sep 2026); **single maintainer**; MIT; on PyPI | **Best fit** — see below |
| **sysml2py** (Westfall-io) | Python | textX | Items/Parts/Attributes only (no ports, connections, requirements) | Dormant since May 2024 (v0.5.3) | Insufficient coverage |
| **PySysML2** (DAF Digital Transformation Office) | Python | ANTLR4 | Partial subset ("basic elements") | 2 commits, research project report | Not production-grade |
| **sysml-v2-parser** (crates.io), **SysML2Tools** (demaconsulting, .NET), **tree-sitter-sysml** | Rust / C# / tree-sitter | — | Varies | Early-stage | Wrong ecosystem for this project |

Not applicable: `SysML-v2-API-Python-Client` (REST client for model *repositories*,
does not parse textual notation).

## Empirical evaluation of sysmlpy

Tested with `sysmlpy==0.96.4` against this repo's
`examples/aircraft_subset/*.sysml` (scratch venv, scripts preserved under
`/tmp/opencode/sysmlpy-eval/`).

### Works

- **Multi-file, same-package merge**: `load_files([...])` merges the 4 aircraft
  files into one `Aircraft` package — exactly matches the custom parser's
  directory mode.
- **All core constructs parse**: `part def`, `port def` with attributes,
  `requirement def` with `doc`, typed attributes (both `x : Real` and `x: Real`),
  `in`/`out` ports, typed part usages, `connect a.p to b.q;`, `doc` comments on
  packages/definitions/members, `specializes` and `redefines` (both are standard
  SysML v2 keywords — confirmed against the current OMG grammar).
- **Navigation**: `model.packages`, `pkg.find_one("AircraftComposition")`,
  `find(sysml_type="port")`, `typed_by_name`, `Attribute.get_value()`,
  requirement `doc` text — everything the generators need to walk.
- **Semantic analysis** (`analyze(model)`): symbol resolution, import checking,
  well-formedness rules — beyond what the custom parser offers. Warns that
  `Real`/`Integer` should be imported from `ScalarValues` (true per standard).
- **Round-trip export**: `dump()` re-emits valid SysML v2 including doc comments,
  part typings, and `connect` statements (basis for `generate sysml` / `sync ssd`).
- **Programmatic construction** + `dump()` for the SSD → SysML direction.
- Dependencies: `pint`, `pyyaml`, `antlr4-python3-runtime` — `pint` is already in
  the dependency tree via `pyssp_standard`.

### Dialect gaps found (our side, not theirs)

Standard SysML v2 rejects three things our dialect allows:

1. `attribute comment = "..."` — `comment` is a **reserved keyword** in SysML v2
   (annotation syntax). Occurs in `part_definitions.sysml`. Fix: rename the
   attribute (e.g. `note`).
2. `attribute x = [0.0, 10.0, 20.0];` — bracket list literals are not SysML v2;
   the standard form is a tuple: `attribute x = (0.0, 10.0, 20.0);`. Occurs in
   `part_definitions.sysml` and is produced/consumed by the custom exporter.
3. `remove <member>;` — does not exist in SysML v2 at all. Used only by the
   submodule's inheritance tests; no downstream consumer in this repo. Fix: drop
   the feature (its merge behavior can be re-expressed with redefinition or by
   restructuring definitions).

(`part def D : B` colon inheritance is also non-standard — but our parser
already rejects it too, so nothing changes there.)

### API gaps that need adapters or small upstream PRs

- **Port direction** after parsing: the `in`/`out` prefix is preserved (grammar
  `dump()` shows `in port feedbackBus: T;`) but not surfaced on the public
  `Port` object. Either walk `port.grammar.prefix...` (internal, brittle) or
  upstream a `Port.direction` population in `load_from_grammar`.
- **Connection endpoints**: `connect a.p to b.q` parses and round-trips, but the
  public `Connection` object does not expose structured `from`/`to` ends; they
  live in the grammar layer. The SSD generator needs `(src_part, src_port,
  dst_part, dst_port)` tuples — a small adapter or upstream PR.
- Export formatting differs from the custom exporter (`part autopilot:
  AutopilotModule;` spacing, per-source-file grouping via `export_declared()`).
  `sync ssd` and `generate sysml` tests compare against the current layout and
  would be rewritten around `dump()` / the JSON interchange format.

## Recommendation

1. **Adopt `sysmlpy` as the parsing base** for a deprecation of `pycps_sysmlv2`,
   behind a thin adapter module in `pyssp_sysml2` that reproduces the operations
   the generators actually use (load-dir, find part def, ports with direction,
   attributes with values/types, connections with endpoints, requirements with
   doc text, model build + export).
2. **Fix our dialect first** (rename `comment` attributes, tuple lists, drop
   `remove`) — this is required for *any* conformant parser, including the
   official pilot implementation, and is a small mechanical change.
3. **De-scope the unused inheritance machinery** (`specializes`/`redefines`/
   `remove`, `inheritance.py`, `export_declared` merge semantics) from the
   migration — nothing in this repo uses it; re-add on demand later via
   sysmlpy's redefinition support if needed.
4. **Mitigate the bus-factor risk**: sysmlpy is MIT, on PyPI, generated from a
   community-maintained grammar that tracks OMG releases, and passes the pilot
   implementation's own XPect conformance suite — but it is a single-maintainer,
   2026-vintage project (8 GitHub stars). Pin an exact version, vendor it as a
   git submodule (as done today for `pycps_sysmlv2`) if forkability matters, and
   keep the adapter thin so the parser can be swapped again.
5. If JVM weight is acceptable and maximum authority is required, the fallback
   is the **official SysML v2 Pilot Implementation** driven headlessly — but it
   changes the deployment story of a `pip install`-able CLI considerably.

## Migration sketch

| Step | Change |
|---|---|
| 1 | Dialect fixes in examples + any user models (`comment`, lists, `remove`) |
| 2 | New `src/pyssp_sysml2/parser_adapter.py`: `load(path) -> Architecture` facade over `sysmlpy.load_files` |
| 3 | Port `ssd.py`, `ssv.py`, `fmi.py` reads from adapter (drop `NodeType`/`refs`/`defs` walking) |
| 4 | Rework `sysml.py` + `sync.py` export path on `dump()`; normalize expected outputs in tests |
| 5 | Remove `pycps_sysmlv2` submodule + its git dependency |
