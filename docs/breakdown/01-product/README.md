---
title: Product
summary: The parameter-set dialect promised to model authors and integrators.
---

# Product

Parameter interfaces, sets, bindings, application rules, types, names, and the
retired flat form.

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **CP-001** [Parameter model](parameter-model.md) — Parameter interfaces, parameter sets, and set usages separate a component surface from reusable values.
- **CP-002** [Parameter bindings](parameter-bindings.md) — Identity binds match member names; explicit binds rename per member; one set usage uses one form.
- **CP-003** [Set application](set-application.md) — One component may take several sets when their target members are disjoint; nested targets use component paths.
- **CP-004** [Types and lists](types-and-lists.md) — Supported primitive parameter types and fixed list multiplicity, with their expansion rules and errors.
- **CP-007** [Interface-only models](interface-only-models.md) — A component can declare a parameter interface without applying a set; generators emit connectors and defaults only.
- **CP-008** [Parameter dialect markers](parameter-dialect-markers.md) — ParameterInterface and ParameterSet are project markers, not SysML v2 library types, and bind is a mapping declaration.
- **CP-009** [Minimum complete model](minimum-complete-model.md) — A complete interface, set, usage, and bind, with the artifacts it produces.
- **CP-010** [Identity binding](identity-binding.md) — A whole-set bind matches member names and becomes an SSP ParameterBinding with a prefix and no SSM.
- **CP-011** [Explicit binding](explicit-binding.md) — Per-member binds rename each member and become an inline SSD mapping or a standalone SSM.
- **CP-012** [Bind shapes](bind-shapes.md) — The accepted bind forms, from identity through nested targets and lists.
- **CP-013** [Nested set targets](nested-set-targets.md) — Set targets use the component hierarchy; there is no separate set-group path.
- **CP-014** [Naming rules](naming-rules.md) — Which declared, port, and synthesized names the dialect accepts.
- **CP-015** [Unsupported parameter shapes](unsupported-parameter-shapes.md) — Parameter forms the dialect rejects or does not implement.
- **INFO-024** [Retired flat-attribute parameters](retired-flat-parameters.md) — Direct parameter attributes on a part are rejected; parameters use an interface and a bound set.
- **INFO-025** [Glossary](glossary.md) — Terms for the simulation-modeling dialect and its status labels.
- **INFO-026** [Invalid bind shapes](invalid-bind-shapes.md) — One set usage uses one form; whole-to-member, over-deep paths, and mixed forms are rejected.
<!-- pb:index:end -->
