# Case: `selection`

Input documents for model-level configuration derivation and analysis plans.

## Artifacts

| Path | Kind |
| --- | --- |
| `selection.sysml` | Input |
| `deep-nesting.sysml` | Input (three-level configuration) |
| `unknown-variant.sysml` | Input (invalid configuration) |
| `non-point.sysml` | Input (invalid configuration) |
| `chain-errors.sysml` | Input (non-linear chain, non-SspModel supertype) |
| `multi-redefine.sysml` | Input (one usage, two redefined features) |
| `binding-errors.sysml` | Input (five invalid binding values) |
| `nested-unknown-variant.sysml` | Input (unknown variant in a nested scope) |
| `rebinding.sysml` | Input (inherited binding overridden) |
| `attribute-binding.sysml` | Input (model attribute point bound by a configuration) |
| `attribute-ambiguous.sysml` | Input (same-named attribute usages) |
| `unresolvable-variant.sysml` | Input (variant type not declared) |
| `analysis-order.sysml` | Input (declaration-order analyses) |

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

The remaining documents isolate one rejection or derivation rule each:

- `chain-errors.sysml` declares `Linear`, which specialises two `SspModel`
  definitions, and `Orphan`, whose only supertype is not marked `SspModel`.
  It pins the two chain-shape errors, the second through `model_root`.
- `multi-redefine.sysml` binds one usage with two `:>>` targets, so no single
  variation point is named.
- `binding-errors.sysml` holds five configurations whose binding value is
  invalid: a qualified value of another point's type, an unqualified value
  naming no local usage, a local usage with zero or two subsetting targets, and
  a local usage specialising another point's member.
- `nested-unknown-variant.sysml` names an undeclared variant inside the selected
  outer variant's body, so the failure is reported at `top.inner`.
- `rebinding.sysml` binds `path` in `Nested` and again in `Direct`; the more
  derived configuration wins and the inherited selection is discarded.
- `attribute-binding.sysml` binds the model's attribute point in a configuration
  (`attribute :>> scenario = ScenarioChoice::nominalK3;`), not in an analysis;
  the plan is `legal`, generation targets `Root`, and `BadConfigured` pins the
  unknown-variant rejection. The root model build resolves the same bare key:
  analysis part subtrees are not duplicate candidates.
- `attribute-ambiguous.sysml` pins that two genuinely distinct attribute usages
  (`mode`, `inner.x.mode`) are still ambiguous for a bare key.
- `unresolvable-variant.sysml` selects a variant whose declared type is missing;
  derivation succeeds, while `resolve_selected` rejects the type.
- `analysis-order.sysml` declares three analyses in a known order; one composes
  a configuration, one another configuration, and one the plain root.

The tests prove that derivation replaces the retired `pyssp_selection` control
attribute: the configuration is the single authored source, the map is stable,
and every reachable point must be selected.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-30 | Created | Authored selection and analysis plans. |
| 2026-10-30 | Replaced the control attribute with configurations | Slice 2 of `IMP-106`. |
| 2026-10-30 | Added chain, binding, rebinding, attribute, and plan cases | Cover configuration-derivation branches and error paths. |
