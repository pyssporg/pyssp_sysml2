---
id: INFO-047
type: info
title: SSM artifact
summary: One SSM per explicit set-component application holds source-to-target MappingEntry rows; identity binds are skipped.
date: 2026-11-05
status: current
---

# SSM artifact

```bash
pyssp generate ssm \
  --architecture examples/parameter_sets \
  --composition AircraftComposition \
  --output-dir build/generated/parameter_mappings
```

Behavior:

- one `.ssm` per explicit `(set, component)` application;
- identity binds are skipped because they use an SSD prefix;
- file name `<SetName>_<ComponentName>.ssm`;
- nested component paths replace dots with underscores, so `outer.inner` becomes
  `outer_inner.ssm`.

Each entry is `<ssm:MappingEntry source="n_waypoints"
target="autopilot.waypointCount" />`. List entries expand on both sides.

`generate ssd` writes the same mapping inline by default, so a standalone SSM
is optional. Use `generate ssm` for external consumers or inspection.
