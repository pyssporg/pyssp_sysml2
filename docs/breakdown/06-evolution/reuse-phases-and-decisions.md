---
id: IMP-004
type: imp
title: Reuse phases and open decisions
summary: Implementation proceeds through model, generation, sync, and optional interface inheritance; six decisions remain open.
date: 2026-10-22
status: current
---

# Reuse phases and open decisions

Status: proposed, not implemented.

## Implementation phases

### Phase A: model support

- Add `Attribute.redefines: tuple[str, ...]`.
- Capture redefinition targets in the loader.
- Emit `:>> Qualified::member` in the exporter.
- Add load and export round-trip tests.
- Add transitive marker helpers.
- Add an effective-attribute resolver with cycle and conflict checks.

### Phase B: generation

- Use effective set members in SSV, SSD, SSM, and disjointness checks.
- Use effective interface members in FMI and SSD when interface inheritance is
  supported.
- Keep base definitions out of SSP unless applied.

### Phase C: sync

- Preserve existing inheritance by name.
- Apply the override-overlay policy.
- Keep synthesized flat sets flat.
- Document base-set update effects.

### Phase D: optional interface inheritance

- Use the same effective-attribute resolver for parameter interfaces.
- Flatten for FMI and SSD.
- Preserve inherited interface definitions during sync.
- Defer if only set reuse is needed.

## Out of scope

- Nested set containment.
- Dotted parameter group names.
- Reconstructing inheritance from SSV or SSD.
- Abstract set definitions unless a concrete need appears.
- Namespacing within a set; member names must be unique across the effective
  union.

## Open decisions

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
