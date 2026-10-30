---
id: INFO-002
type: info
title: Model structure
summary: Files merge into one package; leaf parts become FMU components and parts with subparts become nested systems.
date: 2026-10-23
status: current
---

# Model structure

## Files and packages

The loader accepts one `.sysml` file or a directory. Directory loading is:

- non-recursive;
- only `*.sysml` files;
- sorted by file name;
- merged into one architecture;
- expected to use the same package name in every file.

Definitions keep their `source_file`, which matters for export and sync.

The loader is deliberately non-validating:

- unresolved references return `None` from `resolve_part` / `resolve_port`;
- generators raise the context-specific error;
- a model can load even if a generator rejects it later.

## SysML v2 syntax constraints

- List values use tuples: `attribute xs = (1.0, 2.0);`. Bracket lists are not
  SysML v2 syntax.
- `comment` is a reserved keyword. Do not use it as an attribute name.
- Bind and connect endpoints are feature chains, for example
  `bind autopilot.parameters.waypointCount = nominal.n_waypoints;` and
  `connect src.outSig to dst.inSig;`.
- One package per architecture. The adapter resolves names inside one package;
  imports across packages are not part of the repository workflow.

## Part definitions: FMU components and nested systems

The SSD distinction is structural:

- A `part def` with no subparts becomes an `ssd:Component` with an FMU source.
- A `part def` with subparts becomes an `ssd:System`.
- The part usage name becomes the SSD element name.
- The part definition name determines the FMU source stem for a leaf.

The definition name determines `resources/<Definition>.fmu` when the leaf
declares `fmu_meta.source`. Dots in a definition name become underscores in the
FMU filename.

A nested system cannot also be an FMU. FMU metadata is meaningful only on a
leaf; a part with both subparts and `fmu_meta` is rejected.

A `part def` with no subparts is a leaf component even if the SSD originally had
a `System` element with no children. No structural marker distinguishes an
empty system from an FMU leaf; this is a documented round-trip limitation.

## Variation points

- A `variation part def` carries `is_variation`; its `variant` members sit in
  `variants` and never in `parts`.
- A `variation part` usage carries `is_variation` and its own `variants`; the
  members belong to the usage, not to the definition that encloses it.
- A `variation attribute def` carries `is_variation`; its `variant attribute`
  members sit in `variants` and never in `attributes`.
- A `VariantMember` has a name, a usage kind (`part` or `attribute`), an
  optional declared type, and an optional body.
- A variant body (`variant part name { ... }`) is a `VariantBody` with the
  variant's own subparts, connections, bindings, and attribute usages. It is the
  implicit anonymous definition of that variant usage; its part and connection
  members never enter the enclosing definition, while its attributes and
  bindings are merged there on selection.
- A body with no parts and no connections is a statement container: its
  attributes and bindings are merged into the definition that owns the
  variation usage, and the usage is removed on selection, so no empty component
  reaches the SSD.
- A variation usage inside a selected body is a point of its own, selected by
  the dotted path (`path.inner=variant`). Only two levels are supported; a
  third level is rejected, never flattened.
- Bodies, usage-level members, and nested points inside a body are recovered
  from the raw parse tree, because sysmlpy drops them; the model exposes them as
  repo-owned dataclasses.

## Constraints

Constraint capture is repo-owned; `sysmlpy.check_constraints` is unused. A package-level `constraint def` becomes a `ConstraintDefinition` with typed parameters and one source-scanned expression (sysmlpy garbles a definition's grammar dump). A `constraint name : Type { in p = ref; }` becomes a `ConstraintUsage` on its owning part def, bindings in source order; `assert [not] name;` sets `asserted`/`negated`, and an unknown name is rejected. Each binding resolves to `owner path + "." + reference` in the variant selection.
`parameters/constraints.py` walks reachable part usages and evaluates asserted usages after `variation.resolve` over `==`, `!=`, `implies`, `and`, `or`, `xor`, `not`, parentheses, and references (`Type::member` → `member`). Asserted fail/invalid raises before an SSD, SSP, or analysis write; non-asserted usages report `unasserted`; no selection is a no-op.

## Top-level composition

The top composition is a structural container, not a parameter target.

- A top-level `parameters` port is rejected.
- Top-level SSD system parameter connectors are rejected when generating SysML.
- Attach parameter interfaces to component or nested-system usages instead.
- The composition may carry default-experiment control attributes and may have
  ports for structural wiring.
