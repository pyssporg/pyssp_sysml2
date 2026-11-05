---
id: INFO-007
type: info
title: Round-trip and sync
summary: Sync reconciles SSD edits into SysML; preserved, normalized, and lost information is explicit.
date: 2026-11-05
status: current
---

# Round-trip and sync

## Syncing an SSD into SysML

`sync ssd` applies SSD composition edits back to SysML.

Existing architecture:

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

A missing architecture is bootstrapped from the SSD using the same logic as
`generate sysml`; it writes `architecture.sysml` (`INFO-038`).

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
through an interface and SysML-defined sets (`INFO-024`).

Limits and fidelity are `INFO-041`; what survives is `INFO-042`.
