# Case: `selection`

Input documents for model-level configuration derivation and analysis plans.

## Artifacts

| Path | Kind |
| --- | --- |
| `selection.sysml` | Input |
| `deep-nesting.sysml` | Input (three-level configuration) |
| `unknown-variant.sysml` | Input (invalid configuration) |
| `non-point.sysml` | Input (invalid configuration) |

No expected artifact: the tests assert the derived selection maps, the plan
statuses, and the generated analysis descriptor.

## What this case proves

`selection.sysml` declares one analysis per configuration shape:

- a simple structural configuration (`StepSingleSystem`), legal;
- a conditional configuration (`SineTwoSystem`) that binds an illegal pair, so
  its analysis is `violated`;
- an analysis composing the root `System`, which leaves its points unbound and
  is therefore `invalid`;
- a nested configuration (`NestedGainSystem`) whose outer usage specialises the
  `nestedPath` variant and binds the inner stage in its body; the derived map is
  `{"path": "nestedPath", "path.inner_stage": "gainStage"}`;
- a configuration that selects the outer variant but leaves the inner point
  unbound (`NestedUnboundSystem`), `invalid`;
- an analysis-local attribute point (`nominal`) bound by its own feature value;
- an analysis composing the plain root (`PlainSystem`), deriving `{}`.

`unknown-variant.sysml` and `non-point.sysml` are minimal documents for the two
rejection rules: a binding names a variant the point does not declare, and a
redefinition targets a feature that is not a variation point.
`deep-nesting.sysml` proves the recursion is general by binding three levels:
`{"top": "b", "top.inner": "b1", "top.inner.deeper": "c1"}`.

The tests prove that derivation replaces the retired `pyssp_selection` control
attribute: the configuration is the single authored source, the map is stable,
and every reachable point must be selected.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-30 | Created | Authored selection and analysis plans. |
| 2026-10-30 | Replaced the control attribute with configurations | Slice 2 of `IMP-106`. |
