---
title: Evolution
summary: Open candidates: parameter-set reuse, variation selection, and FMI Model Exchange and 3.0 ownership.
---

# Evolution

Not-yet-decided improvements. Current state is never restated here.

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **IMP-001** [Parameter-set reuse contract](reuse-contract.md) — Reuse by inheritance and union; a set inside a set is rejected because SSP parameters are flat.
- **IMP-002** [Effective set member map](reuse-semantics-and-transfer.md) — An effective member map collects inherited members by name, applies overrides, and rejects unresolved conflicts.
- **IMP-003** [Reuse round-trip and sync policy](reuse-roundtrip-and-gap.md) — Generation synthesizes flat sets, while sync preserves inheritance behind an override overlay.
- **IMP-004** [Reuse implementation phases](reuse-phases-and-decisions.md) — Implementation proceeds through model, generation, sync, and optional interface inheritance.
- **IMP-005** [Reuse contract forms: base and additive](reuse-contract-forms.md) — A base set is a normal valued set, and a derived set adds members by specializing it.
- **IMP-006** [Variation points to one SSP per selection](sysml-variation-points-to-one-ssp-per-selection.md) — A declared variation should reach the artifact or fail the build; selection enters from outside and produces one SSP per selection.
- **IMP-007** [Effective sets in application and disjointness](reuse-application.md) — A set usage sees all effective members, and disjointness is checked on effective targets rather than direct attributes.
- **IMP-008** [Effective sets flattened into SSP](reuse-ssp-transfer.md) — One applied effective set produces one flat SSV, one SSD ParameterBinding, and no inheritance metadata in SSP.
- **IMP-010** [Reuse adapter gap](reuse-adapter-gap.md) — pycps_sysml2 cannot yet represent inheritance or redefinition, so the reuse proposal needs model and exporter work there.
- **IMP-011** [Reuse open decisions](reuse-open-decisions.md) — Six choices remain open, and each has a recommended default before implementation starts.
- **IMP-012** [Reuse contract forms: override, union, and conflict](reuse-contract-override-union.md) — Value override uses standard redefinition, multiple inheritance is a union, and a same-member conflict needs explicit redefinition.
- **IMP-013** [Variation capture evidence](variation-capture-evidence.md) — The pinned parser drops variant members and usage-level flags, while the raw tree retains every variant member.
- **IMP-014** [Variation implementation phases](variation-phases.md) — The route runs fail-loud, model, loader, resolve, generate, provenance, and export refusal in seven phases.
- **IMP-015** [Variation risks and open questions](variation-risks-and-questions.md) — Parser coupling, double parsing, model surface, ambiguity, and provenance are the blast radius; three questions stay open.
- **IMP-016** [FMI Model Exchange and FMI 3.0 ownership](fmi-model-exchange-and-fmi3.md) — After the v0.4.0 split, pyfmi_sysml2 owns FMI 2.0 Co-Simulation packaging but no package owns Model Exchange or FMI 3.0.
<!-- pb:index:end -->
