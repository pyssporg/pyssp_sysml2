---
id: INFO-033
type: info
title: Variation points
summary: Variation definitions and usages carry variants and bodies captured as pycps_sysml2 dataclasses.
date: 2026-11-05
status: current
---

# Variation points

## Capturing variation

Variation is captured by `pycps_sysml2` into its dataclasses; this package reads
the resolved result (`INFO-040`).

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
  the dotted path (`path.inner=variant`); a third level is rejected, never
  flattened.
- A model-level configuration is captured on `PartUsage` and `Attribute`
  (`redefines`, `subsets`, `value`, body); selection and plans: `INFO-027`.
