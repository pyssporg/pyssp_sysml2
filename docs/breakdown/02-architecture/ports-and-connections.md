---
id: INFO-003
type: info
title: Ports and connections
summary: Port definitions map to port.attribute connectors; scalar, inferred, canonical, and boundary forms round-trip with limits.
date: 2026-10-23
status: current
---

# Ports and connections

## Port definitions

A port is an `attribute def`-like record of variables:

```sysml
port def Signal {
  attribute x : Real;
  attribute y : Real;
}

part def Source {
  out port outSig : Signal;
}

part def Sink {
  in port inSig : Signal;
}
```

SSD connectors use `port.attribute` names: `Source.outSig.x` and
`Sink.inSig.y`.

## Scalar connectors

A connector without a dot is a scalar connector. The loader normalizes it to a
port with one attribute named `value`.

The reverse direction uses the `pyssp_flat_connector` control attribute. With
it, `generate ssd` emits the connector name `signal` instead of `signal.value`.

A flat port usage name may be quoted, so one FMU variable that is not a SysML
identifier can be its own port:

```sysml
in port 'consumerFeed.X[1]' : RealSignal;
```

`generate ssd` emits the connector `consumerFeed.X[1]` with that port usage's
own direction. This is the way to model a variable namespace with dots or array
brackets, and it is the way to give variables under one prefix independent
input/output directions.

## Fixed port multiplicity

A port usage may declare a fixed multiplicity. It is one port in SysML and one
connector per occurrence in the SSD:

```sysml
out port 'feed.X' : RealSignal[3];
connect source.'feed.X' to sink.'feed.X';
```

`generate ssd` emits `feed.X[1]`, `feed.X[2]`, and `feed.X[3]`, and one
connection per index. Signal indices start at 1 to match FMI array variable
names; parameter lists keep the 0-based SSV convention.

A connection between ports of different fixed multiplicity is rejected.

`sync ssd` still requires `port.attribute` endpoints. Scalar SSD connections
are not syncable.

## Port type compatibility

`generate ssd` and `generate sysml` compare port definitions by identity or
signature. Both endpoints of a connection must resolve to the same effective
port signature. A connection between incompatible port shapes is rejected.

Inferred port definitions are shared by signature, so two different port names
can use the same inferred `Port_N` definition.

## Inferred names and canonicalization

`generate sysml` synthesizes port definitions named `Port_1`, `Port_2`, and so
on. Original SysML port names are not recoverable from an SSD. This is a naming
loss, not a semantic loss.

A port with one attribute is canonicalized to an attribute named `value`. A
source connector `outSig.x` and a destination connector `inSig.y` can therefore
become the same one-attribute port type and round-trip as `outSig.value` and
`inSig.value`. SSP gives attribute names only, not original port definition
names.

## Boundary connections

A connection end without a part names a port of the enclosing part def, the
system boundary:

```sysml
part def Inner {
  in port u : Signal;
  out port v : Signal;
  part gain : Gain;
  connect u to gain.u;
  connect gain.y to v;
}
```

The SSD omits `startElement` or `endElement` for that end. Rules:

- A boundary port at the start of a connection must be declared `in`.
- A boundary port at the end must be declared `out`.
- A connection between two boundary ports is rejected; it would not cross a
  subpart.
- `generate sysml` and `sync ssd` write the same bare-name form back.
