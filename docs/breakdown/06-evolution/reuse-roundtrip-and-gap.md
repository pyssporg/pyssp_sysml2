---
id: IMP-003
type: imp
title: Reuse round-trip and adapter gap
summary: Generation synthesizes flat sets; sync should preserve inheritance; the current model and exporter cannot represent redefinition.
date: 2026-10-22
status: current
---

# Reuse round-trip and adapter gap

Status: proposed, not implemented.

## Generation

`generate sysml --ssd ...` has no inheritance metadata. It should synthesize a
flat set. Inheritance is an authoring-level reuse mechanism, not an SSP
artifact.

## Sync overlay

If `sync ssd` finds an existing set definition with the same name, it should
preserve inheritance:

- If the SSD value differs from an inherited value, add or update a `:>>`
  redefinition on the derived set.
- If the SSD value equals the inherited value, remove a redundant override and
  fall back to the base.
- If the member is new, add a direct attribute.
- If a direct new member is absent from the SSD, remove it.
- Inherited members absent from the SSD keep their base value.

This keeps derived sets small:

```sysml
attribute def AggressiveSet :> NominalSet {
  attribute n_waypoints : Integer :>> NominalSet::n_waypoints = 20;
}
```

Updating a base set affects every derived set that inherits it. That is the
expected consequence of reuse and should be documented in the model.

## Current adapter gap

The current code cannot represent this proposal:

- `is_parameter_set()` and `is_parameter_interface()` check only direct
  `:> ParameterSet` and `:> ParameterInterface`; they are not transitive.
- `parameter_declarations()`, `mapping_entries()`, `write_parameter_set()`,
  `_signature()`, and `add_set()` use only direct `definition.attributes`.
- `parameter_synthesis` clears direct attributes during sync; it does not
  preserve inherited members.
- The repo `Attribute` model has no `redefines` field.
- The loader drops sysmlpy's redefinition information.
- The exporter emits a same-named attribute without `:>>`, so an override would
  not round-trip as a standard SysML redefinition.

The parser already accepts the standard form:

```sysml
attribute y : Real :>> A::y = 2.0;
```

It records the target in the usage through sysmlpy's `_redefined_refs`. The
public `redefined_name` covers only the bare form. The adapter needs to preserve
it.
