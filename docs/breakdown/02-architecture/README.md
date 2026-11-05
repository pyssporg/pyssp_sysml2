---
title: Architecture
summary: How model structure, ports, metadata, naming, generation, and sync fit together.
---

# Architecture

The organizing design of the dialect: files and parts, ports and connections,
control metadata, synthesized names, variation and selection, the generation
pipeline, and round-trip behavior.

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **INFO-002** [Model structure](model-structure.md) — Leaf parts become FMU components and parts with subparts become nested systems; the top composition is a structural container.
- **INFO-003** [Ports and connections](ports-and-connections.md) — Port definitions map to port.attribute connectors; scalar and quoted flat ports round-trip with limits.
- **INFO-004** [Control attributes](control-attributes.md) — pyssp_ attributes carry SSP metadata and are read through pycps_sysml2's ControlAttributes object.
- **INFO-005** [Naming and synthesis](naming-and-synthesis.md) — Artifact names and synthesized definition names form part of the round-trip contract.
- **INFO-006** [Generation pipeline](generation-pipeline.md) — The pipeline starts at a loaded architecture and emits SSD, SSV, SSM, the analysis descriptor, and the packaged SSP.
- **INFO-007** [Round-trip and sync](round-trip-and-sync.md) — Sync reconciles SSD edits into SysML; preserved, normalized, and lost information is explicit.
- **INFO-027** [Selection and configuration](selection-and-plans.md) — An analysis composes a model-level SysML v2 configuration, and pycps_sysml2 derives the variant selection from its bindings.
- **INFO-032** [Loading and files](loading-and-files.md) — The loader merges the primary model root and any included definition roots into one non-validating architecture.
- **INFO-033** [Variation points](variation-points.md) — Variation definitions and usages carry variants and bodies captured as pycps_sysml2 dataclasses.
- **INFO-034** [Constraints](constraints.md) — Constraint definitions and usages are captured and evaluated by pycps_sysml2 during selection.
- **INFO-035** [Boundary connections](boundary-connections.md) — A connection end without a part names a port of the enclosing definition and becomes a bare SSD endpoint.
- **INFO-036** [Port multiplicity and synthesis](port-synthesis.md) — Fixed multiplicity expands to indexed connectors; ports compare by signature and are synthesized as Port_N with a canonical value attribute.
- **INFO-037** [FMU metadata](fmu-metadata.md) — Typed FmuMetadata definitions name the built FMU; pyssp_sysml2 passes source and implementation through without interpreting FMI.
- **INFO-038** [Synthesis source files](synthesis-source-files.md) — Generated and synced definitions are written to fixed files, and each fact is either stored in SysML or derived.
- **INFO-039** [Artifact responsibilities](artifact-responsibilities.md) — Each emitted artifact names its source of truth and what it contains.
- **INFO-040** [Variation selection](variation-selection.md) — An unresolved variation point blocks generation; selection runs on a copy before generation.
- **INFO-041** [Round-trip limits](round-trip-limits.md) — What sync and generate sysml reject, normalize, or cannot reconstruct.
- **INFO-042** [Round-trip preserved and renamed](round-trip-preserved-and-renamed.md) — What a round trip keeps, and what it renames or normalizes.
- **INFO-043** [Analysis plans](analysis-plans.md) — Each analysis resolves to a legal, violated, or invalid plan, and the SSP records its configuration name.
- **INFO-044** [Selection keys and scope](selection-keys-and-scope.md) — Derived keys are canonical paths shared with constraint evaluation, and required points are scoped to the build target.
<!-- pb:index:end -->
