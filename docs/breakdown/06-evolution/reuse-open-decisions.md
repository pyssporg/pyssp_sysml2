---
id: IMP-011
type: imp
title: Reuse open decisions
summary: Six choices remain open, and each has a recommended default before implementation starts.
date: 2026-11-05
status: proposed
---

# Reuse open decisions

Status: proposed, not implemented.

1. Overrides: allow explicit `:>>` redefinitions, or additive-only inheritance?
   Recommended: allow overrides.
2. Multiple inheritance: allow union of multiple base sets with explicit
   conflict resolution? Recommended: yes.
3. Interface inheritance: sets only first, or interfaces too? Recommended: sets
   first, interfaces as a follow-up.
4. Sync policy: preserve inheritance with an override overlay, or flatten?
   Recommended: overlay.
5. `generate sysml` from SSD: acceptable to synthesize a flat set and lose the
   base and derived structure? Recommended: yes.
6. Conflicts: reject two bases defining the same member unless the derived set
   explicitly redefines it? Recommended: yes.

Phases are `IMP-004`; forms are `IMP-005` and `IMP-012`.
