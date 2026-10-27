---
id: INFO-021
type: info
title: CLI and example usage
summary: The pyssp entry point exposes generate and sync subcommands; examples exercise both the CLI and the module API.
date: 2026-10-22
status: current
---

# CLI and example usage

The entry point in `pyproject.toml` is `pyssp = pyssp_sysml2.cli:main`.

Subcommands:

- `pyssp generate ssd`
- `pyssp generate ssv`
- `pyssp generate ssm`
- `pyssp generate fmi`
- `pyssp generate ssp`
- `pyssp generate sysml`
- `pyssp sync ssd`

## Example validation

```bash
bash examples/cli_usage.sh
PYTHONPATH=src python3 examples/module_usage.py
```

If `pyssp` is not installed as a console script, the CLI example falls back to:

```bash
PYTHONPATH=src python3 -m pyssp_sysml2.cli ...
```

## Runnable parameter-set examples

`examples/parameter-sets/` holds self-contained models for the parameter
dialect:

- `identity/` shows matching names, an identity bind, and no SSM.
- `explicit/` shows different set and interface names, per-member binds, and an
  SSM.
- `multiple/` shows two disjoint sets on one component.
- `nested/` shows a set applied to a nested component path.

Each example README states the generation commands and expected artifacts. The
artifact sequence is in `INFO-006`.
