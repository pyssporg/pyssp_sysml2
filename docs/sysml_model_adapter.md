# The `sysml_model` Adapter

`pyssp_sysml2.sysml_model` is the anti-corruption layer between the repo's
generators and the external [sysmlpy](https://github.com/mycr0ft/sysmlpy)
parser (pinned `sysmlpy==0.96.4` in `pyproject.toml`). It replaced the retired
in-repo parser `pycps_sysmlv2` (see `docs/parser_alternatives_evaluation.md`
for the decision).

## Design rule

Only `sysml_model/loader.py` imports `sysmlpy`. Everything else works against
the repo-owned dataclasses in `sysml_model/model.py`:

- `loader.py` — parses `.sysml` files (file or directory, same-package merge)
  into the repo model. All sysmlpy-specific knowledge lives here.
- `model.py` — the stable model (`Architecture`, `PartDefinition`,
  `PortUsage` with `direction`, `Connection` with endpoints, `Attribute` with
  Python-native values). Generators depend only on this.
- `exporter.py` — emits conformant SysML v2 text (grouped per source file)
  directly from the dataclasses, so the output format is a repo contract that
  cannot drift with sysmlpy releases. Round-trip tests
  (`tests/test_sysml_model.py`) re-load exports through sysmlpy to pin the
  syntax.

If sysmlpy's API changes, only `loader.py` needs fixes; if the parser must be
swapped again, only `loader.py` needs rewriting.

## sysmlpy 0.96.4 internals the loader depends on

These are NOT part of sysmlpy's public API and are the first things to check
when upgrading the pin — all isolated at the bottom of `loader.py`
("grammar-layer walks" section):

- **Port direction** lives at `port.grammar.prefix.prefix.prefix.direction`
  (`FeatureDirection.isIn/isOut/isInOut`); the public `Port` has no direction.
- **Connection endpoints** live in
  `ConnectionUsage.part.part.children[].children[].children[]`
  (`OwnedReferenceSubsetting` + `OwnedFeatureChaining`); for a dotted end like
  `src.sig` both names come from the feature-chaining list.
- **Negative literals**: `get_value()` drops a leading unary minus (`-1.5`
  reads as `1.5`); the sign is re-attached from the grammar's
  `UnaryExpression.operator`.
- `get_value()` raises `AttributeError` for value-less attributes, returns
  `'true'`/`'false'`/`'(1.0,2.0)'` as raw *strings* for bool/tuple literals,
  and returns pint `Quantity` for unit literals — all normalized in
  `loader.py` to the legacy value semantics.
- Loading emits a benign one-time `UserWarning` ("DFA cache save failed");
  suppressed at `loader.py` import time.

## Model dialect requirements

`.sysml` inputs must be standard-conformant SysML v2. Two legacy constructs
were removed from this repo's models during the migration:

- list-valued attributes use tuples: `attribute xs = (1.0, 2.0);`
  (bracket lists `[...]` are a syntax error), and
- `comment` is a reserved keyword — attributes may not be named `comment`.

## Behavior notes

- Loading is non-validating: unresolved references surface as
  `Architecture.resolve_part/resolve_port` returning `None`; consumers raise
  their own errors (the retired parser hard-failed at parse time).
- sysmlpy attaches a `doc /* ... */` written above a member to the *owning*
  definition, so per-member docs from sources written in that style land on
  the definition; the exporter emits def-level docs (they round-trip) and
  member docs where the model carries them.
- `export_declared()` groups definitions by their source file (default
  `architecture.sysml`), which is how `sync ssd` writes back
  `composition.sysml` / `part_definitions.sysml` / ... separately; synthesized
  definitions carry `inferred_external_parts.sysml`.
