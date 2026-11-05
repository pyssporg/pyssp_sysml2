---
id: INFO-042
type: info
title: Round-trip preserved and renamed
summary: What a round trip keeps, and what it renames or normalizes.
date: 2026-11-05
status: current
---

# Round-trip preserved and renamed

## Preserved or semantically preserved

- Parameter member names, except reserved or invalid names, which are rejected
  (`CP-014`).
- Parameter values: the SSV is the source of truth for set values.
- Parameter types: primitive types and fixed multiplicities (`CP-004`).
- Interface defaults when sync reconciles an unchanged signature.
- Binding intent: identity becomes prefix, explicit becomes mapping
  (`CP-010`, `CP-011`).
- Nested system structure: nested SSD `System` and nested part definition.
- Connections per system level, including bare-name boundary ends
  (`INFO-035`).
- FMU metadata `implementation` and default-experiment control metadata
  (`INFO-037`, `INFO-004`).
- Unrelated definitions and file layout when syncing; `generate sysml` starts
  fresh.

Renamed or normalized:

- Port definition names become `Port_N`; a single-attribute port attribute is
  canonicalized to `value` (`INFO-036`).
- A scalar connector name maps between `signal` and `signal.value`.
- A parameter interface name becomes `<PartDefinition>Parameters`; a set usage
  name derives from the set name, `parameters` becomes `parameters_set`, with a
  collision suffix (`INFO-005`).
- Composition name is the SSD system name unless `--composition` overrides it;
  package name is `RecoveredFromSSD` for `generate sysml`.
- SSM file name is `<Set>_<Component>.ssm`, with dots replaced by underscores.
