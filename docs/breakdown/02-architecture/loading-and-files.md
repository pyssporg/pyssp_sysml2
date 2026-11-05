---
id: INFO-032
type: info
title: Loading and files
summary: The loader accepts one SysML file or a sorted directory of them and merges them into one non-validating architecture.
date: 2026-11-05
status: current
---

# Loading and files

## Loading and syntax rules

`pycps_sysml2.load()` accepts one `.sysml` file or a directory; definitions keep
their `source_file`, which matters for export and sync. Directory loading is:

- non-recursive;
- only `*.sysml` files;
- sorted by file name;
- merged into one architecture;
- expected to use the same package name in every file.

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
- One package per architecture. Names resolve inside one package; imports
  across packages are not part of the repository workflow.

The loaded `Architecture` is `pycps_sysml2`'s IR; this package consumes it
(`INFO-031`, `INFO-038`).
