---
id: INFO-028
type: info
title: Scope
summary: What belongs in pyssp_sysml2 and what belongs to pycps_sysml2, pyfmi_sysml2, or another package.
date: 2026-11-05
status: current
---

# Scope

Belongs here:

- SSD, SSV, SSM, analysis-descriptor, and packaged-SSP emission.
- SSD to SysML synthesis and `sync ssd`.
- the `pyssp` CLI as the public surface.
- `core/paths.py` and the parameter-dialect synthesis in `parameters/synthesis/`.

Belongs elsewhere:

- SysML v2 parsing, the dataclasses, the dialect markers, parameter interfaces
  and sets with their binds and resolution, control attributes, variation,
  configuration, selection, and constraints: `pycps_sysml2`.
- FMI model descriptions, C headers, Modelica connectors, and the FMU zip:
  `pyfmi_sysml2`.
- the SSP and FMI XML object model: `pyssp_standard`.
- engine execution and result normalisation: `pyssp_simulate`.
- measurement and judgment: `pyssp_vv`.
- workflow composition and scheduling: `pyssp_workflow`.
