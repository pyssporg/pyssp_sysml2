---
title: Verification
summary: Test ownership, validation rules, diagnostics, warnings, and the pre-flight checklist.
---

# Verification

How correctness is checked: which suite owns which behavior, the validation
catalog, and the checks that run before a generator.

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **INFO-015** [Validation of markers and roles](validation-markers-ports-binds.md) — The loader accepts unresolved models; generators validate markers, roles, and the parameters port before writing an artifact.
- **INFO-016** [Validation of sets and disjointness](validation-sets-disjointness.md) — No target parameter may be bound twice; multiple targets must be disjoint because SysML bind is equality, not override.
- **INFO-017** [Validation of FMU metadata](validation-fmu-metadata.md) — FMU metadata must be typed, unique, leaf-only, and use only the known source and implementation string members.
- **INFO-018** [Validation of generation selection](validation-generation-selection.md) — Set selection, referenced SSV and SSM files, and mapping sources each have an explicit diagnostic before output is written.
- **INFO-019** [Warnings](warnings.md) — Warnings do not stop generation; each names an expected design state or a forgotten step without rejecting the model.
- **INFO-049** [Validation of parameter ports and mixing](validation-parameter-ports.md) — A part has at most one parameters port, may not declare flat parameter attributes, and cannot be the composition root.
- **INFO-050** [Validation of set application and binds](validation-set-application-binds.md) — A bind must pair whole set with whole port or one member with one member, and binds live only at the composition root.
- **INFO-051** [Validation of types and multiplicity](validation-types-multiplicity.md) — Set and interface types must match, lists must have a fixed length, and indexed mappings must agree on both sides.
- **INFO-052** [Validation of names](validation-names.md) — pyssp_ and SysML keywords are rejected, parameter names must be flat, and generated set names must stay unique.
- **INFO-053** [Validation of composition and nesting](validation-composition-nesting.md) — Part references must resolve, recursive hierarchies are rejected, and a nested system may own an interface but not FMU metadata.
- **INFO-054** [Validation of sync diagnostics](validation-sync.md) — Sync requires port.attribute connectors, correct boundary directions, complete mappings, and resolvable composition parts.
- **INFO-055** [Validation of SSP packaging](validation-ssp-packaging.md) — Declared sources, FMU readability, connector names and kinds, and implementation must all agree before an archive is committed.
- **INFO-056** [Pre-flight checklist](preflight-checklist.md) — The checklist catches dialect and packaging mistakes before a generator runs.
- **TEST-001** [Test strategy](test-strategy.md) — Behavior-focused tests whose SysML documents are committed files and whose per-test case stays test-local; this repo owns artifact and round-trip evidence.
- **TEST-002** [Layout and golden gates](test-layout-and-goldens.md) — A static layout test guards the shim boundary, and committed conversion goldens are checked byte for byte; FMI goldens are gone.
<!-- pb:index:end -->
