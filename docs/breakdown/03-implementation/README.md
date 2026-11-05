---
title: Implementation
summary: Modules, concrete artifact writers, the shim boundary, and the pycps_sysml2 dependency.
---

# Implementation

Files and concrete writers that realize the architecture, plus the one-minor
compatibility shims left by the v0.4.0 split.

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **INFO-008** [Module map](module-map.md) — pyssp_sysml2 keeps artifact writers and SSD-to-SysML synthesis; the dialect and IR are pycps_sysml2 shims removed in 0.5.0.
- **INFO-009** [SSV artifact](ssv-artifact.md) — One SSV per applied set holds only valued members with flat expanded names; interface defaults are never copied.
- **INFO-010** [SSD artifact](ssd-artifact.md) — generate ssd writes structure, sources, connections, and the default experiment without embedding values.
- **INFO-012** [SSP packaging](ssp-packaging.md) — generate ssp packages the SSD, built FMUs, and applied SSVs into one deterministic archive.
- **INFO-045** [SSD parameter connectors](ssd-parameter-connectors.md) — Interface members become parameter connectors, and list members expand to one indexed connector each.
- **INFO-046** [SSD parameter bindings](ssd-parameter-bindings.md) — Identity binds become prefixed ParameterBindings, explicit binds inline an SSM mapping, all at the top system level.
- **INFO-047** [SSM artifact](ssm-artifact.md) — One SSM per explicit set-component application holds source-to-target MappingEntry rows; identity binds are skipped.
- **INFO-048** [SSP design-first export](ssp-design-first-export.md) — A leaf with no source exports without a flag, a declared but unbuilt source needs allow-missing-fmus, and attach_fmu populates later.
<!-- pb:index:end -->
