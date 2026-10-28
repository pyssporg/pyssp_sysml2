---
id: INFO-013
type: info
title: SysML model adapter
summary: Only loader.py imports sysmlpy; generators use repo-owned dataclasses and a repo-owned exporter.
date: 2026-10-23
status: current
---

# SysML model adapter

`pyssp_sysml2.model` is the anti-corruption layer between the generators
and the external `sysmlpy` parser, pinned `sysmlpy==0.96.4`. It replaced the
retired in-repo parser `pycps_sysmlv2`; see `EVAL-001`.

## Design rule

Only `model/loader.py` imports `sysmlpy`. Everything else works against the
repo-owned dataclasses in `model/model.py`.

- `loader.py` parses `.sysml` files, from a file or directory with same-package
  merge, into the repo model. All sysmlpy-specific knowledge lives here.
- `model.py` defines the stable model: `Architecture`, `PartDefinition`,
  `PortUsage` with `direction`, `Connection` with endpoints, and `Attribute`
  with Python-native values. A `None` part means the enclosing system's port.
  Generators depend only on this.
- `exporter.py` emits conformant SysML v2 text grouped per source file, directly
  from the dataclasses. The output format is a repo contract that does not drift
  with sysmlpy releases. Round-trip tests re-load exports through sysmlpy to pin
  the syntax.

If sysmlpy's API changes, only `loader.py` needs fixes. If the parser is swapped
again, only `loader.py` needs rewriting.

## Behavior notes

- Loading is non-validating. Unresolved references surface as
  `Architecture.resolve_part` or `resolve_port` returning `None`; consumers
  raise their own errors.
- sysmlpy attaches a `doc` written above a member to the owning definition.
  The exporter emits definition-level docs, which round-trip, and member docs
  where the model carries them.
- `export_declared()` groups definitions by source file, default
  `architecture.sysml`. This is how `sync ssd` writes `composition.sysml`,
  `part_definitions.sysml`, and other files separately. Synthesized definitions
  carry `inferred_external_parts.sysml`.
- `bind` statements are stored in source order on their owning part def.
  sysmlpy names unnamed bindings with UUIDs; those names are normalized to
  `None`, and the exporter emits unnamed `bind` lines.
- `attribute def` members keep declared multiplicity, `Real[3]` or `Real[0..*]`.
  Parameter tooling requires a fixed length for SSP output.
- `variant` members, usage-level `variation` flags, and `variation attribute
  def` flags are recovered from the raw parse tree, because sysmlpy drops
  them; only `loader.py` reads that tree.
- A variant body (`variant part name { ... }`) is read from the same tree and
  becomes a repo-owned `VariantBody`: its direct part usages, its connections
  (with `part.port` or boundary-port ends), its bindings, and its attribute
  usages. A body part that is itself a `variation part` keeps its flag and its
  raw-tree variant members, so a dotted selection can resolve it after the
  enclosing body is selected. A member the walk cannot carry (an attribute
  value, nested decomposition, an unknown body item) raises instead of being
  dropped.
- The model exposes variation as `is_variation` and `variants` on part and
  attribute definitions and on part usages; a usage-level point's members live
  in the usage's own `variants`, keyed by its enclosing definition and usage
  name during the walk.
- A redefining port (`out port :>> y : T;`) keeps its declared name; sysmlpy
  gives its parsed name a UUID.
