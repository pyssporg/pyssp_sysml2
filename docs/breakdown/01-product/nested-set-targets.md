---
id: CP-013
type: capability
title: Nested set targets
summary: Set targets use the component hierarchy; there is no separate set-group path.
date: 2026-11-05
status: current
---

# Nested set targets

Set targets use the component hierarchy, not a separate parameter namespace:

```sysml
bind outer.inner.parameters.k = nominal.k;
```

- `outer.inner` is a component path.
- `k` is the interface member.
- There is no set-group path. A set cannot contain a set, so
  `bind outer.inner.parameters.k = nominal.gains.k` is not supported.

The binding stays at the top system level; the target is `outer.inner.k`.

Multiple disjoint sets work at a nested path with targets `outer.inner.count`
and `outer.inner.gain` (`CP-003`).

A nested system can own a parameter interface:

```sysml
part def Outer {
  in port parameters : OuterParameters;
  part inner : Inner;
}

bind outer.parameters.gain = outer_set.g;
```

The SSD has a nested `System name="outer"` with connector `gain`, and the
binding target is `outer.gain`.
