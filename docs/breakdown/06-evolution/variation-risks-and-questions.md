---
id: IMP-015
type: imp
title: Variation risks and open questions
summary: Parser coupling, double parsing, model surface, ambiguity, and provenance are the blast radius; three questions stay open.
date: 2026-11-05
status: proposed
---

# Variation risks and open questions

Status: proposed, not implemented as written here.

**Risks.**
- **Parser coupling**: the raw tree is an internal API; a pin change can break
  the walk without a version signal.
- **Double parse**: one extra parse pass per architecture; acceptable at
  fixture scale, not free.
- **Model surface**: a new field on a dataclass shared by every generator,
  exporter, and sync path.
- **Ambiguity**: a variant member shares a name with a plain part unless the
  field separates them.
- **Scope creep**: `variant connect` and `variant bind` invite a general
  variability engine; the intent forbids it.
- **Provenance**: SSP has no selection slot, so any home is a local convention.
- **Round-trip**: export cannot represent variation, so sync would erase points
  unless it refuses.

**Open questions.**
- Does a selection name the variant, the artifact case, or both?
- Is a missing selection an error, or does an explicit default variant apply?
- Which variation kind comes next: usage-level parts, variant bodies, or
  attribute sets?

The proposal is `IMP-006`; phases are `IMP-014`.
