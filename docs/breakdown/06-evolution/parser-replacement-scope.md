---
id: EVAL-001
type: eval
title: Parser replacement scope and candidates
summary: A conformant parser can replace the custom subset parser; sysmlpy fits the required usage surface best.
date: 2026-10-14
status: current
---

# Parser replacement scope and candidates

Question: can the custom `pycps_sysmlv2` parser, a regex and line-based subset
parser in `3rd_party/pysysml2_cps`, be replaced by a more established
open-source alternative?

Answer: replacement is feasible, and `sysmlpy` is the strongest candidate, with
a caveat about project maturity. The SysML v2 subset this project uses is almost
entirely standard-conformant textual notation. Two constructs in the example
models are non-standard and need mechanical fixes. The submodule's `remove`
statement has no standard equivalent and is dropped.

## Required coverage

Current usage surface across `ssd.py`, `ssv.py`, `fmi.py`, `sysml.py`, and
`sync.py`:

- parse a directory of `.sysml` files that all declare the same package name,
  merged into one model;
- walk `part def` attributes, typed part usages, in and out ports, and `connect`
  statements;
- walk `port def` attributes and `requirement def` doc text;
- read attribute values (numbers, strings, booleans, lists), types (`Real`,
  `Integer`, `Boolean`, `String`), and `doc` comments;
- build a model programmatically and export SysML text for `generate sysml` and
  `sync ssd`.

`specializes`, `redefines`, and `remove` are not used in this repository. They
live only in the submodule's own test suite and its `inheritance.py` and
`exporter.py`.

## Candidate landscape

- **SysML v2 Pilot Implementation** (OMG SST): Java and Xtext, complete
  reference implementation, very active. Most established, but JVM-heavy for a
  pip-installable CLI.
- **Eclipse SysON**: Java, complete, active. A web platform, not an embeddable
  Python library.
- **sysml-2ls / SysIDE**: TypeScript, full 2024-12 specification. LSP and VS
  Code tooling, wrong shape for a generator library.
- **sysmlpy**: Python with ANTLR4. 123/123 OMG XPect conformance, 168/168
  round-trip tests, 1635 tests total, MIT, on PyPI. Very active through 2026 at
  v0.96.4, but single maintainer. Best fit.
- **sysml2py**: Python with textX. Items, Parts, and Attributes only; no ports,
  connections, or requirements. Dormant since May 2024. Insufficient.
- **PySysML2**: Python with ANTLR4. Partial basic-element subset; a research
  project. Not production-grade.
- **sysml-v2-parser**, **SysML2Tools**, and **tree-sitter-sysml**: Rust, C#,
  and tree-sitter. Early stage and wrong ecosystem.
- **SysML-v2-API-Python-Client** is not applicable: it is a REST client for
  model repositories and does not parse textual notation.
