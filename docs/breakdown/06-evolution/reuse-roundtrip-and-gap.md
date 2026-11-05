---
id: IMP-003
type: imp
title: Reuse round-trip and sync policy
summary: Generation synthesizes flat sets, while sync preserves inheritance behind an override overlay.
date: 2026-11-05
status: proposed
---

# Reuse round-trip and sync policy

Status: proposed, not implemented.

**Generation.** `generate sysml --ssd ...` has no inheritance metadata. It should synthesize a
flat set. Inheritance is an authoring-level reuse mechanism, not an SSP
artifact.

**Sync overlay.** If `sync ssd` finds an existing set definition with the same name, it should
preserve inheritance:

- If the SSD value differs from an inherited value, add or update a `:>>`
  redefinition on the derived set.
- If the SSD value equals the inherited value, remove a redundant override and
  fall back to the base.
- If the member is new, add a direct attribute.
- If a direct new member is absent from the SSD, remove it.
- Inherited members absent from the SSD keep their base value.

Updating a base set affects every derived set that inherits it. That is the
expected consequence of reuse and should be documented in the model.

The model and exporter gap is `IMP-010`; phases are `IMP-004`.
