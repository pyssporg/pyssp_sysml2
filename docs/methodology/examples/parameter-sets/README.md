# Parameter-set methodology examples

Each directory is a self-contained SysML model used by
[01 — Parameter sets](../../01-parameter-sets.md). They are runnable, but they
intentionally live under `docs/` so they do not become part of the repository's
main example suite.

| Example | Demonstrates | Composition |
| --- | --- | --- |
| [`identity/`](identity/model.sysml) | Matching names, identity bind, no SSM | `IdentityComposition` |
| [`explicit/`](explicit/model.sysml) | Different set/interface names, per-member binds and SSM | `ExplicitComposition` |
| [`multiple/`](multiple/model.sysml) | Two disjoint sets on one component | `MultipleSetComposition` |
| [`nested/`](nested/model.sysml) | Set applied to a nested component path | `NestedPathComposition` |

Run from the repository root. The `pyssp` console script is assumed to be
installed; otherwise use `PYTHONPATH=src python3 -m pyssp_sysml2.cli`.

## Identity

```bash
pyssp generate ssv \
  --architecture docs/methodology/examples/parameter-sets/identity \
  --composition IdentityComposition \
  --output-dir build/methodology/identity/parameter_sets

pyssp generate ssd \
  --architecture docs/methodology/examples/parameter-sets/identity \
  --composition IdentityComposition \
  --output build/methodology/identity/SystemStructure.ssd

pyssp generate fmi \
  --architecture docs/methodology/examples/parameter-sets/identity \
  --composition IdentityComposition \
  --output-dir build/methodology/identity/model_descriptions
```

Expected:

- `build/methodology/identity/parameter_sets/NominalSet.ssv`
- an SSD `ParameterBinding` with `prefix="autopilot."` and no inline mapping;
- FMI parameter variables `waypointCount`, `waypointX_km[0..2]`.

## Explicit

```bash
pyssp generate ssv \
  --architecture docs/methodology/examples/parameter-sets/explicit \
  --composition ExplicitComposition \
  --output-dir build/methodology/explicit/parameter_sets

pyssp generate ssd \
  --architecture docs/methodology/examples/parameter-sets/explicit \
  --composition ExplicitComposition \
  --output build/methodology/explicit/SystemStructure.ssd

pyssp generate ssm \
  --architecture docs/methodology/examples/parameter-sets/explicit \
  --composition ExplicitComposition \
  --output-dir build/methodology/explicit/parameter_mappings
```

Expected:

- SSM entries renaming `n_waypoints` → `autopilot.waypointCount`;
- list entries `waypoints_x_km[i]` → `autopilot.waypointX_km[i]`;
- `NominalSet_autopilot.ssm`.

The SSD also contains the same mapping inline by default.

## Multiple disjoint sets

```bash
pyssp generate ssv \
  --architecture docs/methodology/examples/parameter-sets/multiple \
  --composition MultipleSetComposition \
  --output-dir build/methodology/multiple/parameter_sets

pyssp generate ssd \
  --architecture docs/methodology/examples/parameter-sets/multiple \
  --composition MultipleSetComposition \
  --output build/methodology/multiple/SystemStructure.ssd
```

Expected:

- `Counts.ssv` and `Gains.ssv`;
- two SSD `ParameterBinding`s;
- targets `controller.count` and `controller.gain`.

## Nested component path

```bash
pyssp generate ssv \
  --architecture docs/methodology/examples/parameter-sets/nested \
  --composition NestedPathComposition \
  --output-dir build/methodology/nested/parameter_sets

pyssp generate ssd \
  --architecture docs/methodology/examples/parameter-sets/nested \
  --composition NestedPathComposition \
  --output build/methodology/nested/SystemStructure.ssd

pyssp generate sysml \
  --ssd build/methodology/nested/SystemStructure.ssd \
  --output build/methodology/nested/recovered.sysml
```

Expected:

- SSD nested shape: `System outer` → `Component inner`;
- mapping target `outer.inner.k`;
- recovered SysML contains `part def outer`, `part inner : Inner;`, and
  `bind NominalSet.k = outer.inner.parameters.k;`.

The `generate sysml` step needs `NominalSet.ssv` to exist under the relative
path referenced by the SSD. Generating the SSV into
`build/methodology/nested/parameter_sets` before the SSD keeps that path
valid.

## What these examples deliberately do not show

- A set inside a set. That is not supported; see
  [the reuse proposal](../../proposals/parameter-set-reuse.md).
- Set inheritance/union with `:>` and `:>>`. Proposed only.
- Top-level composition parameter bags. Rejected by the dialect.
- Overlapping sets on one component. Rejected; the error is documented in
  [04 — Validation catalog](../../04-validation-catalog.md).
