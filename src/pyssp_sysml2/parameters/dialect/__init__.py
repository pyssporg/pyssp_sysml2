"""Parameter interfaces, parameter sets, and SSP mapping helpers.

The dialect this module implements:

- a **parameter interface** is a ``port def`` marked ``:>
  ParameterInterface``;
- a parameter **set** is an ``attribute def`` marked ``:> ParameterSet``;
- a component or nested system exposes an interface through a single
  fixed-name port, ``in port parameters : <Interface>;``;
- a composition applies one or more sets per component usage with ``bind``:
  either a whole-object bind (identity mapping) or one bind per member
  (explicit mapping);
- multiple sets on one component must bind disjoint target members, because
  SysML ``bind`` is equality, not an override.

Everything here works against the repo-owned model; generators only consume
the helpers in this module.
"""
