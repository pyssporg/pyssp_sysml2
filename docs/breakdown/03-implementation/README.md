---
title: Implementation
summary: Modules, concrete artifact writers, adapter boundary, and the pinned parser.
---

# Implementation

Files, scripts, artifact formats, and the concrete adapter that realizes the
architecture.

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **INFO-008** [Module map](module-map.md) — Domain packages, dependencies, and the adapter boundary between generators and the parser.
- **INFO-009** [SSV and SSM artifacts](ssv-and-ssm-artifacts.md) — SSV files hold set values with flat expanded names; SSM files hold explicit source-to-target mappings.
- **INFO-010** [SSD artifact](ssd-artifact.md) — generate ssd writes structure, parameter connectors, bindings, and default experiment without embedding values.
- **INFO-011** [FMI model descriptions](fmi-model-descriptions.md) — One modelDescription.xml per leaf part, with interface defaults as start values and deterministic GUIDs.
- **INFO-012** [SSP packaging](ssp-packaging.md) — generate ssp packages the SSD, built FMUs, and applied SSVs into one deterministic archive.
- **INFO-013** [SysML model adapter](sysml-model-adapter.md) — Only parser.py imports sysmlpy; variation.py walks the raw tree; generators use repo-owned dataclasses and a repo-owned exporter.
- **INFO-014** [sysmlpy pin internals and dialect](sysmlpy-pin-and-dialect.md) — Internal sysmlpy structures the parser depends on, and the standard SysML v2 dialect the adapter accepts.
<!-- pb:index:end -->
