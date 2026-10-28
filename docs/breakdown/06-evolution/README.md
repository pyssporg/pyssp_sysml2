---
title: Evolution
summary: Candidates for change: parameter-set reuse and the parser replacement evaluation.
---

# Evolution

Not-yet-decided improvements. Current state is never restated here.

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **EVAL-001** [Parser replacement scope and candidates](parser-replacement-scope.md) — A conformant parser can replace the custom subset parser; sysmlpy fits the required usage surface best.
- **EVAL-002** [sysmlpy evaluation and recommendation](sysmlpy-evaluation.md) — sysmlpy parses the repository surface and needs thin adapters for port direction, endpoints, and export formatting.
- **IMP-001** [Parameter-set reuse contract](reuse-contract.md) — Reuse by inheritance and union; a set inside a set is rejected because SSP parameters are flat.
- **IMP-002** [Effective set semantics and SSP transfer](reuse-semantics-and-transfer.md) — An effective member map collects inherited members; application and SSP flatten the result into one SSV.
- **IMP-003** [Reuse round-trip and adapter gap](reuse-roundtrip-and-gap.md) — Generation synthesizes flat sets; sync should preserve inheritance; the current model and exporter cannot represent redefinition.
- **IMP-004** [Reuse phases and open decisions](reuse-phases-and-decisions.md) — Implementation proceeds through model, generation, sync, and optional interface inheritance; six decisions remain open.
- **IMP-005** [Reuse contract forms](reuse-contract-forms.md) — Base sets, additive reuse, value override by redefinition, multiple inheritance as union, and explicit conflict resolution.
- **IMP-006** [SysML variation points to one SSP per selection](sysml-variation-points-to-one-ssp-per-selection.md) — Capture variation and variant members through the raw parse tree, fail loud today, and generate one SSP per explicit selection.
<!-- pb:index:end -->
