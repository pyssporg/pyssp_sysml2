---
id: INFO-002
type: info
title: Model structure
summary: Leaf parts become FMU components and parts with subparts become nested systems; the top composition is a structural container.
date: 2026-11-05
status: current
---

# Model structure

## Components and systems

The SSD distinction is structural:

- A `part def` with no subparts becomes an `ssd:Component` with an FMU source.
- A `part def` with subparts becomes an `ssd:System`.
- The part usage name becomes the SSD element name.
- The part definition name determines the FMU source stem for a leaf.

The definition name determines `resources/<Definition>.fmu` when the leaf
declares `fmu_meta.source`. Dots in a definition name become underscores in the
FMU filename.

A nested system cannot also be an FMU. FMU metadata is meaningful only on a
leaf; a part with both subparts and `fmu_meta` is rejected (`INFO-037`).

A `part def` with no subparts is a leaf component even if the SSD originally had
a `System` element with no children. No structural marker distinguishes an
empty system from an FMU leaf; this is a documented round-trip limitation
(`INFO-041`).

The top composition is a structural container, not a parameter target
(`CP-015`). It may carry default-experiment control attributes and may have
ports for structural wiring; a top-level `parameters` port is rejected
(`INFO-004`).
