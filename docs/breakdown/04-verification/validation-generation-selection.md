---
id: INFO-018
type: info
title: Validation of generation selection
summary: Set selection, referenced SSV and SSM files, and mapping sources each have an explicit diagnostic before output is written.
date: 2026-11-05
status: current
---

# Validation of generation selection

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
- `--select` values are `KEY=VARIANT`; a missing `=`, empty key, or duplicate
  point is rejected before generation.
