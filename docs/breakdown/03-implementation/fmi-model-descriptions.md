---
id: INFO-011
type: info
title: FMI model descriptions
summary: One modelDescription.xml per leaf part, with interface defaults as start values and deterministic GUIDs.
date: 2026-10-23
status: current
---

# FMI model descriptions

```bash
pyssp generate fmi \
  --architecture examples/parameter_sets \
  --composition AircraftComposition \
  --output-dir build/generated/model_descriptions
```

Behavior:

- only leaf part definitions get a model description;
- nested leaf components are discovered recursively;
- definitions are deduplicated by part definition name;
- output is `<PartDefinitionName>/modelDescription.xml`;
- `modelName` is `<CompositionName>.<PartDefinitionName>`;
- `CoSimulation/@modelIdentifier` is the part definition name;
- parameters are emitted before port variables;
- parameter `start` values come from the interface, not from an applied set;
- `variableNamingConvention` is `structured`;
- GUIDs are deterministic for a given composition and part name;
- `fmiVersion` is `"2.0"` and every GUID derives from one fixed namespace, so
  changing either is an artifact-contract change;
- `generationDateAndTime` is the current UTC time by default, injectable with
  `generation_time=` (or by replacing `pyssp_sysml2.fmi.utc_now`), so a fixed
  clock makes two runs byte-identical;
- nothing is written outside `output_dir`: generation never creates files next
  to the package.

A parameter is emitted as a `ScalarVariable` with `causality="parameter"` and
`variability="fixed"`, with the primitive type element carrying the optional
`start` attribute.

A set value such as `n_waypoints = 25` does not become an FMI start value. It is
applied later through the SSD/SSV binding.

A system part definition with an interface does not get an FMI model
description because it has subparts and is not a leaf FMU. Its interface can
still become SSD system connectors and a parameter target.
