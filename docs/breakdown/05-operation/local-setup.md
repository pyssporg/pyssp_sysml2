---
id: INFO-020
type: info
title: Local setup
summary: Create a virtual environment, install dependencies, and install the package editable.
date: 2026-10-22
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

`requirements_local.txt` is for local or shared development setups where
dependencies are available from local paths instead of remote package indexes.

For this repository, the local setup is often the most reliable option:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_local.txt
pip install -e .
```

The editable install provides the `pyssp` console script. Without it, run the
module directly with `PYTHONPATH=src python3 -m pyssp_sysml2.cli`.
