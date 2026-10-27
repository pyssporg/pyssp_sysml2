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
- **CP-004** [Types, lists, and names](types-lists-names.md) — Supported primitive types, fixed list multiplicity, the reserved parameters port, and naming limits.
- **CP-007** [Interface-only models](interface-only-models.md) — A component can declare a parameter interface without applying a set; generators emit connectors and defaults only.
- **INFO-024** [Retired flat-attribute parameters](retired-flat-parameters.md) — Direct parameter attributes on a part are rejected; parameters use an interface and a bound set.
- **INFO-025** [Glossary](glossary.md) — Terms for the simulation-modeling dialect and its status labels.
- **INFO-026** [Invalid bind shapes](invalid-bind-shapes.md) — One set usage uses one form; whole-to-member, over-deep paths, and mixed forms are rejected.
<!-- pb:index:end -->
