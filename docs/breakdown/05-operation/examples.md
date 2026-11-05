---
id: INFO-057
type: info
title: Runnable examples
summary: cli_usage.sh and module_usage.py walk the CLI and Python API, and examples/parameter-sets holds four dialect models.
date: 2026-11-05
status: current
---

# Runnable examples

```bash
bash examples/cli_usage.sh
PYTHONPATH=src python3 examples/module_usage.py
```

Each script defaults to `examples/aircraft_subset` and
`AircraftComposition`, and writes under `build/generated`.

`examples/parameter-sets/` holds self-contained models for the parameter
dialect:

- `identity/` shows matching names, an identity bind, and no SSM.
- `explicit/` shows different set and interface names, per-member binds, and an
  SSM.
- `multiple/` shows two disjoint sets on one component.
- `nested/` shows a set applied to a nested component path.

Each example README states its generation commands and expected artifacts. The
artifact sequence is in `INFO-006`.
