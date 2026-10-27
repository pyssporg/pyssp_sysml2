---
id: INFO-018
type: info
title: Validation of generation, sync, and packaging
summary: Set selection, referenced SSV/SSM files, connector mappings, boundary ports, and FMU packaging each have explicit diagnostics.
date: 2026-10-23
status: current
---

# Validation of generation, sync, and packaging

## Generation selection

- `--output` requires exactly one set. Otherwise
  `A single --output file requires exactly one parameter set; selected N`.
- `--set` must name a known set.
- A set must have values to produce an SSV.
- A referenced SSV must exist, otherwise
  `Parameter set source not found: ...`.
- A referenced SSM must exist.
- Mapping sources must exist in the SSV.
- A bound component must have parameter connectors.
- Set members must exist on the component.

## Sync diagnostics

- Sync connections must use `port.attribute` form.
- Boundary ports must point the right way: `in` at the start, `out` at the
  end.
- Boundary connections must cross a subpart; boundary-to-boundary connections
  are rejected.
- Boundary ports must be declared on the enclosing system.
- Sync requires complete attribute mappings; partial mappings are rejected.
- Sync requires compatible ports.
- Unknown sources can be rejected with `references unknown part source '...'`.
  `sync ssd --no-synthesize` fails instead of creating a part definition.
- An empty component source must match an existing part.
- Unknown ports can be rejected.
- The composition must exist; otherwise `Part not found: ...`.

## SSP packaging

- A declared FMU source must exist unless `--allow-missing-fmus` exports the
  design.
- A file source must be a `.fmu` file or an extracted FMU directory.
- An extracted source must be readable as an FMU.
- Two part definitions cannot map to the same resource name with different
  sources.
- SSD connector names must exist in the FMU.
- SSD connector kinds must match the FMU causality.
- Component implementation must match the FMU interface.

`--skip-fmu-validation` bypasses the model-description name, connector-kind, and
implementation checks. It still requires every declared source to exist and
packages the FMUs. `--allow-missing-fmus` additionally tolerates a missing
declared source; those components keep `resources/<PartDefinition>.fmu`, are
exported without a resource, and are reported as warnings.
