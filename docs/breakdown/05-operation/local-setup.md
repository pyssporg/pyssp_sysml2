---
id: INFO-020
type: info
title: Local setup
summary: Create a virtual environment, install the two direct-URL dependencies, and install the package editable; sysmlpy is transitive.
date: 2026-11-05
status: current
---

# Local setup

Standard setup:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

`requirements_local.txt` is for local or shared development where
`experimental_pyssp_standard` comes from a sibling checkout (in the flat
ecosystem workspace) instead of the pinned git reference.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_local.txt
pip install -e .
```

`pyproject.toml` declares two direct-URL wheels:

- `pycps-sysml2` 0.1.0, which pins `sysmlpy==0.96.4` itself;
- `experimental-pyssp-standard` 0.9.2.dev0.

`sysmlpy` is no longer a direct dependency: this package never imports the
grammar (`AD-004`). The editable install provides the `pyssp` console script.
Without it, run `PYTHONPATH=src python3 -m pyssp_sysml2.cli`.
