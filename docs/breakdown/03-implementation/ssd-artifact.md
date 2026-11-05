---
id: INFO-010
type: info
title: SSD artifact
summary: generate ssd writes structure, sources, connections, and the default experiment without embedding values.
date: 2026-11-05
status: current
---

# SSD artifact

`generate ssd` writes one `SystemStructure.ssd` and embeds no set values.

```bash
pyssp generate ssd \
  --architecture examples/parameter_sets \
  --composition AircraftComposition \
  --output build/generated/SystemStructure.ssd
```

## Structure

- A leaf part definition becomes an `ssd:Component`.
- A part definition with subparts becomes a nested `ssd:System`.
- The part usage name becomes the SSD element name.
- The part definition name determines `resources/<Definition>.fmu` for a leaf
  that declares `fmu_meta.source`.
- A leaf without `fmu_meta.source` gets an empty `Component/@source`.
- `fmu_meta.implementation` sets `Component/@implementation`.
- Connections are written per system level.
- Composition control attributes become
  `<ssd:DefaultExperiment startTime="0" stopTime="3600" />`.

Parameter connectors are `INFO-045`; parameter bindings are `INFO-046`.

`generate ssd` rejects a parameter interface on the top composition:

```text
Top-level composition parameter interfaces are not supported;
attach parameter interfaces to component usages
```
