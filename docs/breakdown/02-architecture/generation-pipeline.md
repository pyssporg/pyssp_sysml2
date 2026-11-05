---
id: INFO-006
type: info
title: Generation pipeline
summary: The pipeline starts at a loaded architecture and emits SSD, SSV, SSM, the analysis descriptor, and the packaged SSP.
date: 2026-11-05
status: current
---

# Generation pipeline

## Two directions

The pipeline starts at a loaded `Architecture` from `pycps_sysml2`
(`INFO-032`) and has two directions:

- A SysML model produces `parameter_sets/*.ssv`, `*.ssm`,
  `SystemStructure.ssd`, an analysis descriptor, and a packaged SSP.
- An SSD plus its referenced SSV/SSM files produce a SysML model through
  `generate sysml` or `sync ssd`.

SSV, SSM, SSD, and SSP are separate outputs. `generate ssd` does not embed
parameter values; it references an SSV and optionally inlines a mapping.
FMI output is not a stage here; it is `pyfmi_sysml2`'s (`INFO-031`).

Per-artifact sources are `INFO-039`; variation selection is `INFO-040`.

Practical ordering:

1. Generate SSV and SSD from SysML.
2. Optionally generate standalone SSM files for inspection.
3. Package built FMUs, SSD, and applied sets as an SSP.
4. Edit the SSD externally, then `sync ssd` to bring structural changes back.
5. Or run `generate sysml` to synthesize a fresh SysML model from the SSD.

`generate sysml` and `sync ssd` need the SSV/SSM files referenced by the SSD.
Keep the parameter directory next to the SSD or preserve relative paths.
