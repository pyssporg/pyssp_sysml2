---
id: CP-003
type: capability
title: Set application
summary: One component may take several sets when their target members are disjoint; nested targets use component paths.
date: 2026-10-23
status: current
---

# Set application

## Multiple sets on one component

A component may have several applied sets, provided their target members are
disjoint.

```sysml
bind comp.parameters.count = counts.n;
bind comp.parameters.gain = gains.k;
```

This produces two SSVs (`Counts.ssv`, `Gains.ssv`), two SSD
`ParameterBinding`s, and two SSMs when explicit mappings are exported
separately.

Overlapping targets are rejected:

```text
Multiple parameter sets bind 'comp.count': counts_a, counts_b.
Use disjoint target members.
```

The dialect rejects overlap instead of inventing precedence. SysML `bind` is an
equality constraint, not an assignment or override. SSP defines precedence for
multiple `ParameterBinding`s, but the SysML dialect does not invent an order.
Disjoint targets keep the mapping deterministic.

List members are whole-feature targets. A bind addresses the whole `xs` list,
not one index. Two sets that both bind `xs` overlap even if their SSVs mention
different indices.

One set definition can be applied to several component usages. The generator
writes one SSV and two `ParameterBinding`s. Disjointness is evaluated per
component.

## Nested part paths

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
and `outer.inner.gain`.

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
