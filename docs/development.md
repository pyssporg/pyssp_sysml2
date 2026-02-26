# Development Guide

This document is for maintainers and contributors.

## Architecture Overview

Core modules:

- `src/pyssp_sysml2/ssd.py`: generates `SystemStructure.ssd`
- `src/pyssp_sysml2/ssv.py`: generates `parameters.ssv`
- `src/pyssp_sysml2/fmi.py`: generates `modelDescription.xml` files
- `src/pyssp_sysml2/cli.py`: CLI entrypoint (`pyssp`)
- `src/pyssp_sysml2/paths.py`: default paths/composition constants

Dependencies:

- `pycps_sysmlv2` for SysML parsing (`load_system`)
- `pyssp_standard` for SSP/FMI XML object handling

## Local Setup


```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

requirements_local.txt is for utilizing local installs of modules for shared development between module and sub-module

## Tests

Run:

```bash
./venv/bin/python -m pytest -q
```

Behavior:

- Generates/updates reference artifacts under `tests/reference` for git diff comparison
- Keeps generated files in repo (no cleanup)
- Normalizes `generationDateAndTime` to a fixed value to avoid timestamp-only diffs

Reference files produced by tests:

- `tests/reference/SystemStructure.ssd`
- `tests/reference/parameters.ssv`
- `tests/reference/model_descriptions/*/modelDescription.xml`

## CLI Contract

Entry point (`pyproject.toml`):

- `pyssp = pyssp_sysml2.cli:main`

Subcommands:

- `pyssp generate ssd`
- `pyssp generate ssv`
- `pyssp generate fmi`

## Example Validation

```bash
bash examples/cli_usage.sh
PYTHONPATH=src python examples/module_usage.py
```

## Troubleshooting

If `pyssp` is not found after install:

```bash
pip install -e .
python -m pyssp_sysml2.cli --help
```

If dependency resolution from `requirements.txt` fails in your environment, use `requirements_local.txt` with bundled third-party packages.
