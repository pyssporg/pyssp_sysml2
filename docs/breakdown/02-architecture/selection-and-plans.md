---
id: INFO-027
type: info
title: Selection and plans
summary: An analysis composes a model-level SysML v2 configuration; the adapter derives the variant selection from its bindings, evaluates constraints, and classifies the analysis as legal, violated, or invalid.
date: 2026-10-30
status: current
---

# Selection and plans

## Authored selection

SysML v2 defines variation points and variants but no selection construct. The
adapter uses the standard 100% configuration: a part definition specialises the
root composition and binds each variation usage with a redefinition and a
feature value.

```
part def StepSystem :> System {
  part :>> source = SourceChoice::step;
}
```

An analysis composes the configuration, not the root. There is one mechanism:
the retired `pyssp_selection` control attribute has no replacement path
(`AD-002` is superseded by `AD-003`).

A binding value is either qualified (`SourceChoice::step`) or the name of a
local usage that specialises a variant
(`part nestedGainPath :> PathChoice::nestedPath { ... }`). Reaching a nested
point requires the outer variant: the configuration binds the outer usage to
that local usage, and the local usage's body binds the inner point. An
analysis-local attribute point carries its own value
(`attribute scenario : ScenarioChoice = ScenarioChoice::nominalK3;`).

## Derivation

`parameters/configuration.py` derives the selection:

- `model_root` walks single-parent specialisation from the composed definition
  to the outermost composition before the `SspModel` marker.
- `configuration_name` returns the composed definition's name, or `None` when
  the analysis composes the root.
- `derived_selection` starts from the root's members, applies every
  redefinition in chain order, and descends into a selected part variant's type
  for nested points, prefixing keys `<outer>.<inner>`.

An override must target a variation point in the current scope; a qualified
value must name the point's variation definition and one of its variants; an
unqualified value must name a local usage with exactly one subsetting target.
Every reachable point must be selected, and an unbound point is an error, never
a silently unselected artifact.

## Plans

`parameters/selection.py` returns an `AnalysisPlan` per `Analysis`:

- `legal`: the selection resolves and every asserted constraint passes;
- `violated`: the selection resolves but an asserted constraint fails;
- `invalid`: the configuration does not resolve, a point is unbound, or a
  constraint could not be evaluated.

`configuration` names the composed configuration, or is `None` for the root.
A fixture pins the expected `legal` and `violated` names; the adapter computes
the partition, so the fixture keeps only its claim. Constraints come from the
effective members of a part definition, so a configuration is judged by the
asserted usages it inherits from its family, evaluated at the composed usage's
path.

## Canonical keys

Derived keys are relative to the composed model (`path`, `path.inner_stage`) or
bare for an analysis-local usage (`scenario`). `variation.resolve_selected`
returns the resolved architecture and the canonical map keyed by the target
composition's usage paths (`source` for a model, `sut.source` for an analysis).
Generation passes that map to constraint evaluation, so variation and
constraints share one key language (`AD-001`).

A key matches an exact path or a dotted suffix of one, so a selection authored
relative to the model addresses the same usage in an analysis. An ambiguous
match is an error.

## Scoped requirements

Required variation points are scoped to the target: a model build requires only
its own composition's points, while an analysis build requires its own and its
model's points. Keys accepted from a composing analysis are allowed but not
required, so one per-analysis selection map reaches both generators unchanged.
