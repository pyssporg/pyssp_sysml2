---
title: Verification
summary: Test strategy, validation rules, diagnostics, warnings, and the pre-flight checklist.
---

# Verification

How correctness is checked: the test strategy, the validation catalog, and the
checks that run before a generator.

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **INFO-015** [Validation of markers, ports, and binds](validation-markers-ports-binds.md) — The loader accepts unresolved models; generators validate markers, the parameters port, flat attributes, and bind shapes.
- **INFO-016** [Validation of sets, types, and names](validation-sets-types-names.md) — Overlapping targets are rejected; types and multiplicities must match; reserved names and dotted names are rejected.
- **INFO-017** [Validation of FMU metadata and composition](validation-metadata-composition.md) — Metadata must be typed, unique, leaf-only, and use known string members; part hierarchies must resolve and stay acyclic.
- **INFO-018** [Validation of generation, sync, and packaging](validation-generation-sync-packaging.md) — Set selection, referenced SSV/SSM files, connector mappings, boundary ports, and FMU packaging each have explicit diagnostics.
- **INFO-019** [Warnings and pre-flight checklist](warnings-and-preflight.md) — Warnings do not stop generation; the checklist catches dialect mistakes before a generator runs.
- **TEST-001** [Test strategy](test-strategy.md) — Small behavior-focused tests with test-local SysML snippets and no shared fixtures by default.
<!-- pb:index:end -->
