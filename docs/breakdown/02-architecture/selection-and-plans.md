---
id: INFO-027
type: info
title: Selection and plans
summary: An analysis authors its variant selection as pyssp_selection; the adapter canonicalizes it, evaluates constraints, and classifies the analysis as legal, violated, or invalid.
date: 2026-10-30
status: current
---

# Selection and plans

## Authored selection

An analysis may declare its variant selection with one control attribute:

```
attribute pyssp_selection = "source=stepImplementation;gain=twoStages";
```

The value uses the same `key=variant` language as the CLI `--select` flag; a
dotted key addresses a nested point (`path.inner_stage=gainStage`). Because the
name carries the `pyssp_` prefix, every generator skips it as model data. An
explicit `--select` wins, so a caller can force a combination for testing.

An analysis composing a varying model without a selection is an error, never
silently unselected.

## Plans

`parameters/selection.py` parses the attribute and returns an `AnalysisPlan` per
`Analysis`:

- `legal`: the selection resolves and every asserted constraint passes;
- `violated`: the selection resolves but an asserted constraint fails;
- `invalid`: the selection is missing, malformed, or does not resolve, or a
  constraint could not be evaluated.

A fixture pins the expected `legal` and `violated` names; the adapter computes
the partition, so the fixture keeps only its claim.

## Canonical keys

`variation.resolve_selected` returns the resolved architecture and the selection
map keyed by the target composition's usage paths (`source` for a model,
`sut.source` for an analysis). Generation passes that canonical map to
constraint evaluation, so variation and constraints share one key language.

A key matches an exact path or a dotted suffix of one, so a selection authored
relative to the model (`path.inner_stage`) addresses the same usage in an
analysis (`sut.path.inner_stage`). An ambiguous match is an error.

## Scoped requirements

Required variation points are scoped to the target: a model build requires only
its own composition's points, while an analysis build requires its own and its
model's points. Keys accepted from a composing analysis are allowed but not
required, so one per-analysis selection map reaches both generators unchanged.
