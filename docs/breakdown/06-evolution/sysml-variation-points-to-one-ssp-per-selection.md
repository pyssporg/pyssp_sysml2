---
id: IMP-006
type: imp
title: Variation points to one SSP per selection
summary: A declared variation should reach the artifact or fail the build; selection enters from outside and produces one SSP per selection.
date: 2026-11-05
status: proposed
---

# Variation points to one SSP per selection

Status: proposed, not implemented as written here.

A variation point is a SysML 2.0 definition or usage marked `variation` whose
alternatives are `variant` members. Selection has no home in SysML, so it enters
from outside and produces one artifact per selection.

## Proposal

- Capture variation through the adapter, not a parser fork.
- Selection enters on the command line, not inside the architecture.
- Generation baseline: one SSP per selection.
- Provenance: the selection is written to an `extra/` entry in the package.
- SysML generation and SSD sync refuse an architecture that carries variation.

Evidence is `IMP-013`; phases are `IMP-014`; risks are `IMP-015`.
