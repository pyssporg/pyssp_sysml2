---
id: INFO-009
type: info
title: SSV and SSM artifacts
summary: SSV files hold set values with flat expanded names; SSM files hold explicit source-to-target mappings.
date: 2026-10-23
status: current
---

# SSV and SSM artifacts

## SSV generation

```bash
pyssp generate ssv \
  --architecture examples/parameter_sets \
  --composition AircraftComposition \
  --output-dir build/generated/parameter_sets
```

Default behavior:

- one `.ssv` per applied parameter set;
- file name `<SetDefinitionName>.ssv`;
- a selected attribute variant's type is the set definition, so the file holds
  that variant's values;
- only members with values are written;
- list members expand to `name[0]`, `name[1]`, and so on;
- interface defaults are not copied into the SSV.

Selection options:

- `--set NominalSet` selects one named set and is repeatable.
- `--all-sets` selects every set definition, applied or not.
- `--set NominalSet --output build/nominal.ssv` writes exactly one set to one
  explicit file. `--output` rejects a selection with more than one set.

The SSV root is `<ssv:ParameterSet version="1.0" name="NominalSet">`. Each
parameter carries its primitive type element, for example
`<ssv:Parameter name="n_waypoints"><ssv:Integer value="10" /></ssv:Parameter>`.
List entries are separate parameters such as `waypoints_x_km[0]`.

If the applied set has no values, `write_parameter_set` raises instead of
writing an empty file. An interface-only model produces no SSV.

A parameter set declared in the composition (`attribute nominal : NominalSet;`)
but never bound to a component is not exported and produces no SSD
`ParameterBinding`. Mapping generation reports it with a `UserWarning` naming
the set, so a forgotten `bind` is visible instead of silently empty.

## SSM generation

```bash
pyssp generate ssm \
  --architecture examples/parameter_sets \
  --composition AircraftComposition \
  --output-dir build/generated/parameter_mappings
```

Behavior:

- one `.ssm` per explicit `(set, component)` application;
- identity binds are skipped because they use an SSD prefix;
- file name `<SetName>_<ComponentName>.ssm`;
- nested component paths replace dots with underscores, so `outer.inner` becomes
  `outer_inner.ssm`.

Each entry is `<ssm:MappingEntry source="n_waypoints"
target="autopilot.waypointCount" />`. List entries expand on both sides.

`generate ssd` writes the same mapping inline by default, so a standalone SSM
is optional. Use `generate ssm` for external consumers or inspection.
