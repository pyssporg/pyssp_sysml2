---
id: INFO-032
type: info
title: Loading and files
summary: The loader merges the primary model root and any included definition roots into one non-validating architecture.
date: 2026-11-05
status: current
---

# Loading and files

## Loading and syntax rules

`pycps_sysml2.load()` takes one primary model root plus any number of included
definition roots. The primary root is one `.sysml` file or a directory; its
definitions keep their `source_file`, which matters for export and sync.
Directory loading is:

- non-recursive;
- only `*.sysml` files;
- sorted by file name;
- merged into one architecture;
- expected to use the same package name in every file.

Included roots come after the primary: `load(model, *includes)`, or the
remaining elements of a sequence whose first element is the model. Each is a
file or a directory with the same directory rules. They merge their definitions
into the primary architecture and need not share its package name, because they
supply vocabulary rather than composition. A definition the model also declares
is an error, never an override; one name supplied by two included roots is also
an error.

The loader is deliberately non-validating:

- unresolved references return `None` from `resolve_part` / `resolve_port`;
- generators raise the context-specific error;
- a model can load even if a generator rejects it later.

SysML v2 syntax constraints:

- List values use tuples: `attribute xs = (1.0, 2.0);`. Bracket lists are not
  SysML v2 syntax.
- `comment` is a reserved keyword. Do not use it as an attribute name.
- Bind and connect endpoints are feature chains, for example
  `bind autopilot.parameters.waypointCount = nominal.n_waypoints;` and
  `connect src.outSig to dst.inSig;`.
- Primary files share one package. Included roots may declare any package,
  because they supply vocabulary; imports across packages are not part of the
  repository workflow.

The loaded `Architecture` is `pycps_sysml2`'s IR; this package consumes it
(`INFO-031`, `INFO-038`).

`pycps_sysml2.load(model, *includes)` merges shared dialect definitions, and
the generators expose that as keyword-only `includes`. The usual element is
`pycps_sysml2.core_definitions()`, the packaged `definitions/core.sysml`
(`package PysspCore`). It is opt-in: empty `includes` is the default and loads
only the model's own declarations, so a model that still declares the markers
keeps working unchanged. Included names are excluded from export; the CLI's
`--core-definitions` adds this one include after repeated `--architecture`
roots.
