# Development Guide

This document is for maintainers and contributors.

If you are using the package (not developing it), start with `README.md`.

## Architecture Overview

Core modules:

- `src/pyssp_sysml2/ssd.py`: generates `SystemStructure.ssd`
- `src/pyssp_sysml2/ssv.py`: generates `parameters.ssv`
- `src/pyssp_sysml2/fmi.py`: generates `modelDescription.xml` files
- `src/pyssp_sysml2/sysml.py`: generates a minimal SysML model from SSD
- `src/pyssp_sysml2/sync.py`: syncs SSD composition edits back into SysML
- `src/pyssp_sysml2/cli.py`: CLI entrypoint (`pyssp`)
- `src/pyssp_sysml2/paths.py`: default paths/composition constants

Dependencies:

- `pycps_sysmlv2` for SysML parsing (`SysMLParser(...).parse().get_def(NodeType.Part, ...)`)
- `pyssp_standard` for SSP/FMI XML object handling

## Local Setup


```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

`requirements_local.txt` is for local/shared development setups where dependencies are
available from local paths instead of remote package indexes.

For this repository, that local setup is often the most reliable option:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_local.txt
pip install -e .
```

## Tests

Run:

```bash
./venv/bin/python -m pytest -q
```

Behavior:

- Uses small explicit SysML snippets written per test case under `tmp_path`
- Follows a one-model-per-behavior style where practical, to keep test intent explicit
- Keeps generated artifacts inside pytest temporary directories
- Treats readability of tests as a primary concern because this repo is used for experimentation as well as regression coverage

Test strategy:

- Optimize for clear, editable tests over maximal reuse.
- Prefer standalone test-local model setup over shared external fixtures or reference files.
- Make each test generic and behavior-focused: one small architecture, one behavior under test.
- When checking generated artifacts, prefer concise text summaries over structural XML traversal when possible.
- If comparing two file formats, convert both to small text views first so the assertion reads as a format-agnostic behavior check.
- Keep assertions close to the behavior being validated; avoid large golden files unless the full artifact text is itself the contract.
- It is acceptable to duplicate a small amount of setup when that keeps the test easier to read and modify.

## CLI Contract

Entry point (`pyproject.toml`):

- `pyssp = pyssp_sysml2.cli:main`

Subcommands:

- `pyssp generate ssd`
- `pyssp generate ssv`
- `pyssp generate fmi`
- `pyssp generate sysml`
- `pyssp sync ssd`

## Example Validation

```bash
bash examples/cli_usage.sh
PYTHONPATH=src python3 examples/module_usage.py
```

If `pyssp` is not installed as a console script, the CLI example falls back to:

```bash
PYTHONPATH=src python3 -m pyssp_sysml2.cli ...
```

## Troubleshooting

If `pyssp` is not found after install:

```bash
pip install -e .
python3 -m pyssp_sysml2.cli --help
```

If dependency resolution from `requirements.txt` fails in your environment, use `requirements_local.txt` with bundled third-party packages.

If `sync ssd` fails on external SSD files, check the SSD shape first:

- connectors must be in `port.attribute` form
- partial attribute mappings are rejected
- nested SSD systems are rejected
