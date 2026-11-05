---
id: IMP-014
type: imp
title: Variation implementation phases
summary: The route runs fail-loud, model, loader, resolve, generate, provenance, and export refusal in seven phases.
date: 2026-11-05
status: proposed
---

# Variation implementation phases

Status: proposed, not implemented as written here.

1. **Fail loud**: detect a reachable variation point and reject the build with
   an actionable message.
2. **Model**: add the variation flag and a variant-member list to the definition
   and usage dataclasses.
3. **Loader**: read the definition flag from the grammar object and members from
   the raw tree.
4. **Resolve**: substitute the selected alternative before generation; reject
   unknown, duplicate, and missing selections.
5. **Generate**: one package and one artifact directory per selection, named
   after the selection.
6. **Provenance**: record the selection outside the SSP. Home undecided.
7. **Export**: refuse SysML export for an architecture that carries variation.

The proposal is `IMP-006`; evidence is `IMP-013`; risks are `IMP-015`.
