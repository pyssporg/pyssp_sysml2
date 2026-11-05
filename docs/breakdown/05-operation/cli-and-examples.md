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

`generate fmi` is gone. It prints an error naming `pyfmi_sysml2` and exits 1:

```text
`generate fmi` was removed in pyssp_sysml2 0.4.0: FMI model descriptions
now come from pyfmi_sysml2 (install pyfmi-sysml2, then run
`pyfmi model-description`).
```

If `pyssp` is not installed as a console script, run the module:
`PYTHONPATH=src python3 -m pyssp_sysml2.cli ...`.
