---
id: CP-002
type: capability
title: Parameter bindings
summary: Identity binds match member names; explicit binds rename per member; one set usage uses one form.
date: 2026-11-05
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
be the same (`CP-010`). One set usage uses one form: `INFO-026`.
