---
id: INFO-022
type: info
title: Troubleshooting
summary: Missing console script, dependency resolution, generate fmi, and SSD shape failures have direct fixes.
date: 2026-11-05
status: current
---

# Troubleshooting

If `pyssp` is not found after install:

```bash
pip install -e .
python3 -m pyssp_sysml2.cli --help
```

If dependency resolution from `requirements-dev.txt` fails, reinstall it with
the sibling `experimental_pyssp_standard`
checkout (`INFO-020`).

If `generate fmi` fails, that subcommand no longer exists. Install
`pyfmi_sysml2` and run `pyfmi model-description` (`INFO-058`).

If `sync ssd` fails on external SSD files, check the SSD shape first:

- connectors must be in `port.attribute` form;
- partial attribute mappings are rejected;
- nested SSD systems are supported recursively for parts, connections, and
  parameters;
- a nested system with no matching SysML part definition is synthesized unless
  `--no-synthesize` is used.

For generation and packaging diagnostics, see `INFO-018`. For warnings that do
not stop generation, see `INFO-019`.
