---
id: INFO-007
type: info
title: Round-trip and sync
summary: Sync reconciles SSD edits into SysML; preserved, normalized, and lost information is explicit.
date: 2026-10-23
status: current
---

# Round-trip and sync

`sync ssd` applies SSD composition edits back to SysML.

## Existing architecture

- The existing model is loaded.
- If it already uses the parameter dialect, the dialect is reconciled.
- Parts and connections are recursively reconciled at every nested system
  level.
- Components can be added, removed, or retyped from their `source`.
- New component and port definitions are synthesized into
  `inferred_external_parts.sysml`.
- New parameter interfaces and sets are synthesized into
  `parameter_sets.sysml`.
- Existing definitions stay in their original `source_file`, so multi-file
  layouts are preserved.
- Unrelated definitions are preserved.

## Missing architecture

Sync bootstraps a model from the SSD using the same logic as `generate sysml`.
It writes `architecture.sysml`.

## Parameter reconciliation

If the existing model uses interfaces and sets, sync:

- removes old top-level set usages and parameter binds;
- rebuilds them from SSD/SSV/SSM;
- reuses an existing set definition by name;
- reuses or merges synthesized set definitions by signature when building a
  fresh model;
- updates set values;
- preserves interface defaults and docs when the signature is unchanged;
- removes a port when the SSD no longer has parameter connectors.

Flat-attribute architectures are rejected: components must declare parameters
through an interface and SysML-defined sets.

## Limits

- SSD connection endpoints must be in `port.attribute` form.
- Partial attribute mappings on a connection are rejected.
- Incompatible connected ports are rejected.
- Unknown component sources are synthesized by default; `--no-synthesize`
  fails instead.
- A childless SSD `System` can regenerate as a leaf component.
- Set inheritance and union are not implemented; see `IMP-001`.
- Flat parameter attributes are retired.
- `pyssp_implementation` and `pyssp_parameter_set` are retired.

## Preserved or semantically preserved

- Parameter member names, except reserved or invalid names, which are rejected.
- Parameter values: the SSV is the source of truth for set values.
- Parameter types: primitive types and fixed multiplicities.
- Interface defaults when sync reconciles an unchanged signature.
- Binding intent: identity becomes prefix, explicit becomes mapping.
- Nested system structure: nested SSD `System` and nested part definition.
- Connections per system level, including bare-name boundary ends.
- FMU metadata `implementation` and default-experiment control metadata.
- Unrelated definitions and file layout when syncing; `generate sysml` starts
  fresh.

## Renamed or normalized

- Port definition names become `Port_N`.
- A single-attribute port attribute is canonicalized to `value`.
- A scalar connector name maps between `signal` and `signal.value`.
- A parameter interface name becomes `<PartDefinition>Parameters`.
- A set usage name derives from the set name; `parameters` becomes
  `parameters_set`, with a collision suffix.
- Composition name is the SSD system name unless `--composition` overrides it.
- Package name is `RecoveredFromSSD` for `generate sysml`.
- SSM file name is `<Set>_<Component>.ssm`, with dots replaced by underscores.

## Lost or not reconstructible

- Original port definition names; the SSD stores only connector names.
- Set inheritance and union; not implemented.
- Original multi-file layout in `generate sysml`; it writes one synthesized
  file.
- The distinction between an empty SSD `System` and a leaf component; no
  structural marker.
- Built FMU path (`fmu_meta.source`); a recovered model has no source and
  regenerated components export an empty `source`.
- Exact source formatting and docs; synthesis produces a repo-owned model.
