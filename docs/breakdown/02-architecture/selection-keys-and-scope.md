---
id: INFO-044
type: info
title: Selection keys and scope
summary: Derived keys are canonical paths shared with constraint evaluation, and required points are scoped to the build target.
date: 2026-11-05
status: current
---

# Selection keys and scope

## Keys and required points

Derived keys are relative to the composed model (`path`, `path.inner_stage`) or
bare for an analysis-local usage (`scenario`). `variation.resolve_selected`
returns the resolved architecture and the canonical map keyed by the target
composition's usage paths (`source` for a model, `sut.source` for an analysis).
Generation passes that map to constraint evaluation, so variation and
constraints share one key language (`AD-001`).

A key matches an exact path or a dotted suffix of one, so a selection authored
relative to the model addresses the same usage in an analysis. An ambiguous
match is an error.

Required variation points are scoped to the target: a model build requires only
its own composition's points, while an analysis build requires its own and its
model's points. From a composing analysis, only the usages the analysis declares
itself are accepted, at bare keys; its `sut` subtree is the composed model and is
already accepted unprefixed, so it contributes no second candidate. Accepted
keys are allowed but not required, so one per-analysis selection map reaches both
generators unchanged.

The plan outcomes are `INFO-043`; the authored configuration is `INFO-027`.
