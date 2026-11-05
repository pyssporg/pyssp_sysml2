---
id: INFO-008
type: info
title: Module map
summary: pyssp_sysml2 keeps artifact writers and SSD-to-SysML synthesis; the dialect and IR are pycps_sysml2 shims removed in 0.5.0.
date: 2026-11-05
status: current
---

# Module map

`src/pyssp_sysml2/` is an SSP-artifact package. The package root exposes only
`__init__.py` and `cli.py`.

```text
src/pyssp_sysml2/
├── __init__.py      canonical public surface: 8 generator functions
├── cli.py           `pyssp` entrypoint
├── artifacts/       analysis.py ssd.py ssm.py ssp.py ssv.py
├── sysml/           generate.py sync.py
├── core/            paths.py (real); the rest are shims
├── metadata/        shims
├── model/           shims
└── parameters/      synthesis/ (real); the rest are shims
```

The dialect, IR, names, exporter, variation, markers, parameter resolution,
selection, constraints, and role/dialect policies belong to `pycps_sysml2`
0.1.0, which pins `sysmlpy==0.96.4` itself (`INFO-031`, `AD-004`).

Only two regions below the moved packages still hold code:

- `core/paths.py`, the build and default-path constants;
- `parameters/synthesis/` — `inputs.py`, `interfaces.py`, `application.py`,
  and `generation.py`, the only remaining `pyssp_standard`-touching dialect
  helper. `generation.py` holds `synthesize_parameter_dialect`.

Every other module below `model/`, `core/`, `metadata/`, and `parameters/` is a
one-line re-export shim naming its `pycps_sysml2` owner. The shims keep old
`pyssp_sysml2.<package>` imports working for one minor release and are removed
in v0.5.0. `tests/test_module_layout.py` is the static gate (`TEST-002`).

Dependencies are two direct-URL wheels: `pycps-sysml2` 0.1.0 and
`experimental-pyssp-standard` (`INFO-020`). `sysmlpy` is transitive, never
imported here.

Public functions: `build_ssd`, `generate_ssd`, `generate_parameter_sets`,
`generate_parameter_mappings`, `generate_analysis`, `generate_ssp`,
`generate_sysml_from_ssd`, and `sync_sysml_from_ssd`. Each path-based generator
takes keyword-only `includes` for `pycps_sysml2.load(model, *includes)`; an
empty sequence is the default and `--core-definitions` is off (`INFO-032`,
`INFO-021`).
