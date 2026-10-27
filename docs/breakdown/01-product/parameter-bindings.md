---
id: CP-002
type: capability
title: Parameter bindings
summary: Identity binds match member names; explicit binds rename per member; one set usage uses one form.
date: 2026-10-22
status: current
---

# Parameter bindings

A bind always puts the parameter port on the left:

```text
bind <component-path>.parameters[.<interface-member>] = <set-usage>[.<set-member>]
```

`<component-path>` may contain dots for nested parts. A bind with the set usage
on the left is rejected with the corrected form.

## The naming model

```text
bind autopilot.parameters.waypointCount = nominal.n_waypoints
```

- The **set member name** (`n_waypoints`) becomes the SSV parameter name.
- The **interface member name** (`waypointCount`) becomes the SSD parameter
  connector name and the FMI variable name.
- The **parameter port on the left** determines the SSP hierarchical target
  name, for example `autopilot.waypointCount`.

SSP stores the mapping in the opposite order:

```text
SysML:  bind autopilot.parameters.waypointCount = nominal.n_waypoints;
SSP:    <ssm:MappingEntry source="n_waypoints" target="autopilot.waypointCount"/>
```

An explicit bind is therefore a rename. An identity bind requires the names to
be the same.

## Identity binding

An identity bind applies a whole set by matching member names:

```sysml
bind autopilot.parameters = nominal;
```

Rules:

- Every valued set member must exist in the interface with the same primitive
  type and multiplicity.
- Interface members the set does not provide are ignored by this application.
- A valued set member absent from the interface is an error, never a silent
  skip.
- Lists expand element-wise in the SSP mapping.
- SSP represents an identity bind as a `ParameterBinding` with a prefix and no
  SSM. The prefix means prepend `autopilot.` to every SSV name.

Identity also works with a nested component path. `bind outer.inner.parameters
= nominal;` produces prefix `outer.inner.`.

Identity is not a fallback for renamed members. Use explicit binds instead.

## Explicit per-member binding

Explicit binds are one bind per set member:

```sysml
bind autopilot.parameters.waypointCount = nominal.n_waypoints;
bind autopilot.parameters.waypointX_km = nominal.waypoints_x_km;
```

This produces an SSV with the set names, an SSD `ParameterMapping` with the
renames, and optionally a standalone SSM. The standalone file is named
`<SetName>_<ComponentName>.ssm`; the inline SSD mapping is the default.

An explicit bind may cover a subset of the set. Unapplied valued members produce
a warning: `Parameter set 'NominalSet' members reserve_km are not bound to
autopilot; SSP will ignore them`. This is a warning, not an error.

## Bind-shape cheat sheet

- Apply a set by matching names: `bind autopilot.parameters = nominal;` gives a
  `ParameterBinding` plus prefix.
- Apply one member with a rename:
  `bind autopilot.parameters.count = nominal.n;` gives an inline mapping or
  SSM.
- Apply to a nested component:
  `bind outer.inner.parameters.k = nominal.k;` targets `outer.inner.k`.
- Apply to a nested system port:
  `bind outer.parameters.gain = nominal.g;` targets `outer.gain`.
- Apply two disjoint sets: two binds give two SSVs and two bindings.
- Apply a list: `bind comp.parameters.xs = nominal.xs;` gives element-wise
  `xs[i]` mappings.
- Declare only an interface with no bind: connectors and FMI defaults only.

