---
title: Architecture
summary: How model structure, ports, metadata, naming, generation, and sync fit together.
---

# Architecture

The organizing design of the dialect: files and parts, ports and connections,
control metadata, synthesized names, the generation pipeline, and round-trip
behavior.

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **INFO-002** [Model structure](model-structure.md) — Files merge into one package; leaf parts become FMU components and parts with subparts become nested systems.
- **INFO-003** [Ports and connections](ports-and-connections.md) — Port definitions map to port.attribute connectors; scalar, inferred, canonical, and boundary forms round-trip with limits.
- **INFO-004** [Control attributes and FMU metadata](control-attributes-and-fmu-metadata.md) — pyssp_ attributes carry SSP metadata; typed FmuMetadata definitions carry source and implementation on leaf parts.
- **INFO-005** [Naming and synthesized definitions](naming-and-synthesis.md) — Artifact names and synthesized definition names form part of the round-trip contract.
- **INFO-006** [Generation pipeline](generation-pipeline.md) — SSV, SSM, SSD, FMI, and SSP are separate outputs with distinct sources of truth.
- **INFO-007** [Round-trip and sync](round-trip-and-sync.md) — Sync reconciles SSD edits into SysML; preserved, normalized, and lost information is explicit.
<!-- pb:index:end -->
