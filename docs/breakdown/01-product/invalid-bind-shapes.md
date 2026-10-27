---
id: INFO-026
type: info
title: Invalid bind shapes
summary: One set usage uses one form; whole-to-member, over-deep paths, and mixed forms are rejected.
date: 2026-10-22
status: current
---

# Invalid bind shapes

A single set usage uses one form.

- Mixing identity and explicit binds for one set usage is invalid. Use either a
  whole-object bind or per-member binds for that usage.
- A whole set into one member is rejected.
- A whole port from one set member is rejected.
- A set path deeper than one member is rejected.
- A parameter path deeper than one member is rejected.

Mixing:

```sysml
attribute nominal : NominalSet;

bind autopilot.parameters = nominal;                    // identity
bind autopilot.parameters.count = nominal.n_waypoints;  // invalid mix
```

Rejected shapes:

```sysml
bind autopilot.parameters.count = nominal;           // whole set into one member
bind autopilot.parameters = nominal.n_waypoints;     // whole port from one member
bind autopilot.parameters.count = nominal.a.b;       // set path too deep
bind autopilot.parameters.a.b = nominal.n_waypoints; // parameter path too deep
```

The accepted grammar is
`bind <component-path>.parameters[.<interface-member>] = <set-usage>[.<set-member>]`.
A bind with the set usage on the left is rejected with the rewritten form.
