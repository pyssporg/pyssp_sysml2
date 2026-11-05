---
id: INFO-036
type: info
title: Port multiplicity and synthesis
summary: Fixed multiplicity expands to indexed connectors; ports compare by signature and are synthesized as Port_N with a canonical value attribute.
date: 2026-11-05
status: current
---

# Port multiplicity and synthesis

## Multiplicity, compatibility, and synthesis

A port usage may declare a fixed multiplicity. It is one port in SysML and one
connector per occurrence in the SSD:

```sysml
out port 'feed.X' : RealSignal[3];
connect source.'feed.X' to sink.'feed.X';
```

`generate ssd` emits `feed.X[1]`, `feed.X[2]`, and `feed.X[3]`, and one
connection per index. Signal indices start at 1 to match FMI array variable
names; parameter lists keep the 0-based SSV convention (`CP-004`).

A connection between ports of different fixed multiplicity is rejected.

`sync ssd` still requires `port.attribute` endpoints. Scalar SSD connections
are not syncable.

`generate ssd` and `generate sysml` compare port definitions by identity or
signature. Both endpoints of a connection must resolve to the same effective
port signature. A connection between incompatible port shapes is rejected.

Inferred port definitions are shared by signature, so two different port names
can use the same inferred `Port_N` definition.

`generate sysml` synthesizes port definitions named `Port_1`, `Port_2`, and so
on. Original SysML port names are not recoverable from an SSD. This is a naming
loss, not a semantic loss (`INFO-042`).

A port with one attribute is canonicalized to an attribute named `value`. A
source connector `outSig.x` and a destination connector `inSig.y` can therefore
become the same one-attribute port type and round-trip as `outSig.value` and
`inSig.value`. SSP gives attribute names only, not original port definition
names.
