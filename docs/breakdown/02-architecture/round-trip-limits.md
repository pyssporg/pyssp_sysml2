---
id: INFO-041
type: info
title: Round-trip limits
summary: What sync and generate sysml reject, normalize, or cannot reconstruct.
date: 2026-11-05
status: current
---

# Round-trip limits

## Rejections and losses

- SSD connection endpoints must be in `port.attribute` form; partial attribute
  mappings and incompatible connected ports are rejected (`INFO-036`).
- Unknown component sources are synthesized by default; `--no-synthesize`
  fails instead.
- Top-level SSD system parameter connectors are rejected when generating
  SysML.
- A childless SSD `System` can regenerate as a leaf component; no structural
  marker distinguishes the two (`INFO-002`).
- Set inheritance and union are not implemented; see `IMP-001`.
- Flat parameter attributes, `pyssp_implementation`, and `pyssp_parameter_set`
  are retired (`INFO-024`, `INFO-004`).
- `generate sysml` and `sync ssd` refuse to rewrite an architecture carrying
  variation points; SysML export does not represent them and would erase them.
- Original port definition names are lost; the SSD stores only connector names
  (`INFO-036`).
- `generate sysml` cannot reconstruct the original multi-file layout; it writes
  one synthesized file.
- A recovered model has no built `fmu_meta.source`, so regenerated components
  export an empty `source` (`INFO-037`).
- Exact source formatting and docs are not preserved; synthesis produces a
  repo-owned model.
