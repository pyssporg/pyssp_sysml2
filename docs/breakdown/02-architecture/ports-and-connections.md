---
id: INFO-003
type: info
title: Ports and connections
summary: Port definitions map to port.attribute connectors; scalar and quoted flat ports round-trip with limits.
date: 2026-11-05
status: current
---

# Ports and connections

## Port definitions and scalar connectors

A port is an `attribute def`-like record of variables:

```sysml
port def Signal {
  attribute x : Real;
  attribute y : Real;
}

part def Source {
  out port outSig : Signal;
}
```

SSD connectors use `port.attribute` names: `Source.outSig.x` and
`Sink.inSig.y`.

A connector without a dot is a scalar connector. The loader normalizes it to a
port with one attribute named `value`.

The reverse direction uses the `pyssp_flat_connector` control attribute: with
it, `generate ssd` emits the connector name `signal` instead of `signal.value`,
and the value `false` means not flattened (`INFO-004`).

A flat port usage name may be quoted, so one FMU variable that is not a SysML
identifier can be its own port:

```sysml
in port 'consumerFeed.X[1]' : RealSignal;
```

`generate ssd` emits the connector `consumerFeed.X[1]` with that port usage's
own direction. This is the way to model a variable namespace with dots or array
brackets, and it is the way to give variables under one prefix independent
input/output directions.

Multiplicity, compatibility, and synthesized port names are `INFO-036`;
boundary ends are `INFO-035`.
