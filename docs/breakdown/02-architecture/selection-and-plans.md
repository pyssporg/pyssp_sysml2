---
id: INFO-027
type: info
title: Selection and configuration
summary: An analysis composes a model-level SysML v2 configuration, and pycps_sysml2 derives the variant selection from its bindings.
date: 2026-11-05
status: current
---

# Selection and configuration

## Authored selection

SysML v2 defines variation points and variants but no selection construct. The
dialect uses the standard 100% configuration: a part definition specialises the
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

`pycps_sysml2` derives the selection from the configuration (`INFO-031`):

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

Generation stays on the root composition. Analysis generation retypes its
`sut` usage to the root before resolution, so inherited parts, ports,
connections, and binds resolve; a configuration name is not a generation
target. Plans are `INFO-043`; key scoping is `INFO-044`.
