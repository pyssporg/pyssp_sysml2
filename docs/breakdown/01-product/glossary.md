---
id: INFO-025
type: info
title: Glossary
summary: Terms for the simulation-modeling dialect and its status labels.
date: 2026-10-22
status: current
---

# Glossary

- **Parameter interface**: a `port def` marked `:> ParameterInterface`. It
  defines names, types, multiplicities, and optional defaults.
- **Parameter set**: an `attribute def` marked `:> ParameterSet`. It holds named
  values applicable to a component.
- **Set usage**: a composition attribute typed by a parameter set, for example
  `attribute nominal : NominalSet;`.
- **Set member**: an attribute of a parameter set, for example
  `n_waypoints = 10`. Its name is the SSV parameter name.
- **Interface member**: an attribute of a parameter interface, for example
  `waypointCount : Integer;`.
- **Identity bind**: a whole-object bind. Names must match and SSP uses a
  `ParameterBinding` prefix instead of an SSM.
- **Explicit bind**: a per-member bind. It produces an SSP mapping entry.
- **Component path**: the dotted part-usage path from the composition root to a
  component or nested system, for example `outer.inner`.
- **Control attribute**: a `pyssp_*` attribute carrying metadata with no
  first-class SysML v2 equivalent. Generators skip it as model data.
- **Leaf component**: a part definition with no subparts. It becomes an SSD
  `Component` and gets an FMI model description.
- **Nested system**: a part definition with subparts. It becomes a nested SSD
  `System`.

## Status labels

- **Implemented**: enforced by current code and covered by tests.
- **Convention**: a project convention encoded in the implementation, even
  where SysML v2 itself is more permissive.
- **Proposed**: a documented design direction, not implemented. Do not use it
  in working models.
