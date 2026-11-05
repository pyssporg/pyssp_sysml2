---
id: INFO-009
type: info
title: SSV artifact
summary: One SSV per applied set holds only valued members with flat expanded names; interface defaults are never copied.
date: 2026-11-05
status: current
---

# SSV artifact

```bash
pyssp generate ssv \
  --architecture examples/parameter_sets \
  --composition AircraftComposition \
  --output-dir build/generated/parameter_sets
```

## Behavior

- One `.ssv` per applied parameter set, named `<SetDefinitionName>.ssv`.
- A selected attribute variant's type is the set definition, so the file holds
  that variant's values.
- Only members with values are written.
- List members expand to `name[0]`, `name[1]`, and so on.
- Interface defaults are not copied into the SSV.
- `--set NominalSet` selects one named set and is repeatable.
- `--all-sets` selects every set definition, applied or not.
- `--set NominalSet --output build/nominal.ssv` writes one set to one file;
  `--output` rejects a selection with more than one set.
- `write_parameter_set` raises on an empty set instead of writing an empty
  file. An interface-only model produces no SSV.

The root is `<ssv:ParameterSet version="1.0" name="NominalSet">`. Each parameter
carries its primitive type element, for example
`<ssv:Parameter name="n_waypoints"><ssv:Integer value="10" /></ssv:Parameter>`.

A set declared in the composition but never bound is not exported and produces
no SSD `ParameterBinding`. Mapping generation reports it with a `UserWarning`
naming the set.
