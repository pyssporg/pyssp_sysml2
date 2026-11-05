---
id: INFO-035
type: info
title: Boundary connections
summary: A connection end without a part names a port of the enclosing definition and becomes a bare SSD endpoint.
date: 2026-11-05
status: current
---

# Boundary connections

## System boundary ends

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
- `generate sysml` and `sync ssd` write the same bare-name form back
  (`INFO-007`).
