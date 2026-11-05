---
id: INFO-031
type: info
title: Ecosystem roles
summary: Which package owns parsing, SSP artifacts, FMI, simulation, judgment, and composition.
date: 2026-11-05
status: current
---

# Ecosystem roles

```text
sysmlpy==0.96.4
   └── pycps_sysml2 0.1.0   parse, IR, names, exporter, variation, dialect,
                            parameters, selection, constraints, roles/policy
        ├── pyssp_sysml2 0.4.0   SSD/SSV/SSM/SSP/analysis, SSD to SysML, CLI
        └── pyfmi_sysml2 0.1.0   modelDescription, C headers, Modelica, FMU zip
```

- **`pycps_sysml2`** owns the SysML v2 dialect: `load()`, the dataclasses, the
  markers, the parameter dialect and its resolution, control attributes,
  variation, configuration, selection, constraints, and the role and dialect
  policies. It has no `pyssp_standard` dependency.
- **`pyssp_sysml2`** emits SSD, SSV, SSM, the analysis descriptor, and the
  packaged SSP, synthesizes and syncs SysML, and provides the `pyssp` CLI.
- **`pyfmi_sysml2`** owns everything FMI.
- **`pyssp_standard`** handles SSP and FMI XML objects; consumed by this package.
- **`pyssp_simulate`** runs engines and normalises results; consumes the
  generated SSP.
- **`pyssp_vv`** measures, judges, and records evidence.
- **`pyssp_workflow`** builds, runs, compares, and verifies; composes the steps.
