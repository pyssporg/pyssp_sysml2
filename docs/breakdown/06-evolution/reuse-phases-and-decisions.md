---
id: IMP-004
type: imp
title: Reuse implementation phases
summary: Implementation proceeds through model, generation, sync, and optional interface inheritance.
date: 2026-11-05
status: proposed
---

# Reuse implementation phases

Status: proposed, not implemented.

**Phase A: model support.**

- Add `Attribute.redefines: tuple[str, ...]` in `pycps_sysml2`.
- Capture redefinition targets in the loader.
- Emit `:>> Qualified::member` in the exporter.
- Add load and export round-trip tests.
- Add transitive marker helpers.
- Add an effective-attribute resolver with cycle and conflict checks.

**Phase B: generation.**

- Use effective set members in SSV, SSD, SSM, and disjointness checks.
- Use effective interface members in SSD when interface inheritance is
  supported.
- Keep base definitions out of SSP unless applied.

**Phase C: sync.**

- Preserve existing inheritance by name.
- Apply the override-overlay policy (`IMP-003`).
- Keep synthesized flat sets flat.
- Document base-set update effects.

**Phase D: optional interface inheritance.**

- Use the same effective-attribute resolver for parameter interfaces.
- Flatten for SSD.
- Preserve inherited interface definitions during sync.
- Defer if only set reuse is needed.

Out of scope: nested set containment, dotted group names, reconstructing
inheritance from SSV or SSD, abstract set definitions without a concrete need,
and namespacing within a set. Open decisions are `IMP-011`.
