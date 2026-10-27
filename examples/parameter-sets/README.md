# Parameter-set examples

Each directory is a self-contained SysML model used by the parameter-set leaves
in the product breakdown (`CP-001` to `CP-004`, index at
`docs/breakdown/README.md`). They run like the other examples under
`examples/`.

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
  --architecture examples/parameter-sets/identity \
  --composition IdentityComposition \
  --output-dir build/parameter-sets/identity/parameter_sets

pyssp generate ssd \
  --architecture examples/parameter-sets/identity \
  --composition IdentityComposition \
  --output build/parameter-sets/identity/SystemStructure.ssd

pyssp generate fmi \
  --architecture examples/parameter-sets/identity \
  --composition IdentityComposition \
  --output-dir build/parameter-sets/identity/model_descriptions
```

Expected:

- `build/parameter-sets/identity/parameter_sets/NominalSet.ssv`
- an SSD `ParameterBinding` with `prefix="autopilot."` and no inline mapping;
- FMI parameter variables `waypointCount`, `waypointX_km[0..2]`.

## Explicit

```bash
pyssp generate ssv \
  --architecture examples/parameter-sets/explicit \
  --composition ExplicitComposition \
  --output-dir build/parameter-sets/explicit/parameter_sets

pyssp generate ssd \
  --architecture examples/parameter-sets/explicit \
  --composition ExplicitComposition \
  --output build/parameter-sets/explicit/SystemStructure.ssd

pyssp generate ssm \
  --architecture examples/parameter-sets/explicit \
  --composition ExplicitComposition \
  --output-dir build/parameter-sets/explicit/parameter_mappings
```

Expected:

- SSM entries renaming `n_waypoints` to `autopilot.waypointCount`;
- list entries `waypoints_x_km[i]` to `autopilot.waypointX_km[i]`;
- `NominalSet_autopilot.ssm`.

The SSD also contains the same mapping inline by default.

## Multiple disjoint sets

```bash
pyssp generate ssv \
  --architecture examples/parameter-sets/multiple \
  --composition MultipleSetComposition \
  --output-dir build/parameter-sets/multiple/parameter_sets

pyssp generate ssd \
  --architecture examples/parameter-sets/multiple \
  --composition MultipleSetComposition \
  --output build/parameter-sets/multiple/SystemStructure.ssd
```

Expected:

- `Counts.ssv` and `Gains.ssv`;
- two SSD `ParameterBinding`s;
- targets `controller.count` and `controller.gain`.

## Nested component path

```bash
pyssp generate ssv \
  --architecture examples/parameter-sets/nested \
  --composition NestedPathComposition \
  --output-dir build/parameter-sets/nested/parameter_sets

pyssp generate ssd \
  --architecture examples/parameter-sets/nested \
  --composition NestedPathComposition \
  --output build/parameter-sets/nested/SystemStructure.ssd

pyssp generate sysml \
  --ssd build/parameter-sets/nested/SystemStructure.ssd \
  --output build/parameter-sets/nested/recovered.sysml
```

Expected:

- SSD nested shape: `System outer` to `Component inner`;
- mapping target `outer.inner.k`;
- recovered SysML contains `part def outer`, `part inner : Inner;`, and
  `bind NominalSet.k = outer.inner.parameters.k;`.

The `generate sysml` step needs `NominalSet.ssv` to exist under the relative
path referenced by the SSD. Generating the SSV into
`build/parameter-sets/nested/parameter_sets` before the SSD keeps that path
valid.

## What these examples deliberately do not show

- A set inside a set. That is not supported; see `IMP-001`.
- Set inheritance or union with `:>` and `:>>`. Proposed only; see `IMP-001`.
- Top-level composition parameter bags. Rejected by the dialect.
- Overlapping sets on one component. Rejected; the error is documented in
  `INFO-016`.
