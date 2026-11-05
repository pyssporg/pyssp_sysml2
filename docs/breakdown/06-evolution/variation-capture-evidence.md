---
id: IMP-013
type: imp
title: Variation capture evidence
summary: The pinned parser drops variant members and usage-level flags, while the raw tree retains every variant member.
date: 2026-11-05
status: proposed
---

# Variation capture evidence

Status: proposed, not implemented as written here.

- **Definition flag survives**: `Part.grammar.prefix.prefix.isVariation` is
  readable, but no dataclass exposed it at proposal time.
- **Usage flag lost**: the occurrence-usage prefix visitor never tests
  `VARIATION`, so usage-level points vanished.
- **Members lost**: the definition-body visitor had no `variantUsageElement`
  branch and returned `None`, filtered out later.
- **Not fixable by upgrade**: the 0.97.1 wheel carried identical code at the
  same lines at proposal time.
- **Raw tree retains all members**: the parser keeps
  `VariantUsageElementContext` nodes with full text.
- **Probe**: five variant members recovered from one file — parts, a connect, a
  bind, and a usage-level part.
- **Silent before the proposal**: generation of an architecture with variation
  succeeded and emitted a variant-less SSD.
- **Worst case measured**: a path variation emitted one component with an empty
  source and no internal parts.
- **Constraint drop confirmed**: constraints parsed and were ignored; the model
  had no constraint element.
- **Vocabulary**: ISO/IEC 26580 delegates selection to an external configurator;
  SysML has no binding time.

Phases are `IMP-014`.
