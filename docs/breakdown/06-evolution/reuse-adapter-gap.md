---
id: IMP-010
type: imp
title: Reuse adapter gap
summary: pycps_sysml2 cannot yet represent inheritance or redefinition, so the reuse proposal needs model and exporter work there.
date: 2026-11-05
status: proposed
---

# Reuse adapter gap

Status: proposed, not implemented.

The reuse proposal needs work in `pycps_sysml2`, which now owns the model:

- `is_parameter_set()` and `is_parameter_interface()` check only direct
  `:> ParameterSet` and `:> ParameterInterface`; they are not transitive.
- `parameter_declarations()`, `mapping_entries()`, `write_parameter_set()`,
  `_signature()`, and `add_set()` use only direct `definition.attributes`.
- `parameter_synthesis` clears direct attributes during sync; it does not
  preserve inherited members.
- The `Attribute` model has no `redefines` field.
- The loader drops redefinition information.
- The exporter emits a same-named attribute without `:>>`, so an override would
  not round-trip as a standard SysML redefinition.

The parser already accepts the standard form:

```sysml
attribute y : Real :>> A::y = 2.0;
```

It records the target in the usage. The public `redefined_name` covers only the
bare form; the model must preserve it. Sync policy is `IMP-003`; phases are
`IMP-004`.
