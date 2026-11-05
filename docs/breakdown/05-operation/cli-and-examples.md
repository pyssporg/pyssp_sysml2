---
id: INFO-021
type: info
title: CLI usage
summary: The pyssp entry point exposes generate and sync subcommands; generate fmi was removed and names pyfmi_sysml2 in its error.
date: 2026-11-05
status: current
---

# CLI usage

The entry point in `pyproject.toml` is `pyssp = pyssp_sysml2.cli:main`.

Subcommands:

- `pyssp generate ssd`
- `pyssp generate ssv`
- `pyssp generate ssm`
- `pyssp generate ssp`
- `pyssp generate sysml`
- `pyssp generate analysis`
- `pyssp sync ssd`

`generate ssd`, `ssv`, `ssm`, `ssp`, and `analysis` accept repeatable
`--select KEY=VARIANT` values; `generate ssp` also accepts `--configuration`
for the selection provenance.

`ssp`, `ssd`, `ssv`, `ssm`, `analysis`, and `sync ssd` accept repeatable
`--architecture` flags. The first occurrence is the model root; every later one
is an included definition root forwarded as `includes`. `--core-definitions` is
sugar for one such include, adding `pycps_sysml2.core_definitions()`
(`SspModel`, `Analysis`, `Experiment`, `ParameterInterface`, `ParameterSet`,
`FmuMetadata`, `SspMetadata`) after any repeated `--architecture` roots. It is
off by default: without the flag a model must declare the markers it uses. The
core definitions belong to `pycps_sysml2`; this package only passes the path to
the loader.

`generate fmi` is gone. It prints an error naming `pyfmi_sysml2` and exits 1:

```text
`generate fmi` was removed in pyssp_sysml2 0.4.0: FMI model descriptions
now come from pyfmi_sysml2 (install pyfmi-sysml2, then run
`pyfmi model-description`).
```

If `pyssp` is not installed as a console script, run the module:
`PYTHONPATH=src python3 -m pyssp_sysml2.cli ...`.
