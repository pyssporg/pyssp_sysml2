---
id: INFO-040
type: info
title: Variation selection
summary: An unresolved variation point blocks generation; selection runs on a copy before generation.
date: 2026-11-05
status: current
---

# Variation selection

## Resolution before generation

Resolution is `pycps_sysml2`'s; this package passes a selection and generates
from the resolved architecture (`INFO-033`).

- A variation point is unresolved until a caller supplies a selection.
- `generate ssd`, `generate ssp`, and `generate analysis` take `selections`, a
  mapping from a part- or attribute-usage path inside the composition to a
  variant name.
- The CLI passes repeatable `--select KEY=VARIANT` values as that mapping.
- Resolution runs on a deep copy of the architecture before generation.
- A variant with a type replaces the usage type; the usage name and the SSD
  element name stay unchanged.
- A variant with a body (`variant part directPath { part gain : Gain; connect u
  to gain.u; }`) is a selection step of its own: resolution synthesizes an
  anonymous `PartDefinition` from the body, carrying the variation point's
  ports, registers it under `<Point>__<variant>`, and retypes the usage to it.
  Generation then emits a subsystem for that usage, with the body's subparts
  and connections; because the definition has subparts, the usage is no longer
  a leaf.
- Whether a body is a component or a statement container depends on what it
  contains, not where the point sits: parts or connections make it a component
  and keep the usage; a body with neither is merged into the definition that
  owns the usage and the usage is removed.
- A body's attribute usages are merged into the owning definition when its
  variant is selected, so references such as `values.height` resolve there.
- A body's bindings are merged into the owning definition's `bindings` in
  declaration order and then consumed through the ordinary applied-set path
  (`CP-003`).
- Body connections that touch a parameter-interface port stay on the captured
  body but are not emitted as SSD connections; parameters are applied with
  binds and mappings, not with `connect`.
- For attribute variation, the selected type becomes the parameter set
  definition, so parameter binds and the emitted SSV use its values.
- Attribute usages on an analysis that composes the generated model are
  selectable from the model's selection.
- A variation usage inside a selected body is itself a point. Resolution runs
  outermost first and looks inner points up by their full dotted path
  (`path.inner=variant`) after the outer body has been synthesized. Only two
  levels are supported; a third level raises a clear error.
- An unselected variation point fails generation; an unselected inner point
  fails with its full dotted path.
- A body that declares a member the adapter cannot carry fails the load rather
  than dropping it.
