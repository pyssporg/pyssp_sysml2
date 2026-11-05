---
id: INFO-043
type: info
title: Analysis plans
summary: Each analysis resolves to a legal, violated, or invalid plan, and the SSP records its configuration name.
date: 2026-11-05
status: current
---

# Analysis plans

## The three outcomes

`pycps_sysml2` returns an `AnalysisPlan` per `Analysis`; this package consumes
it (`INFO-031`, `INFO-034`):

- `legal`: the selection resolves and every asserted constraint passes;
- `violated`: the selection resolves but an asserted constraint fails;
- `invalid`: the configuration does not resolve, a point is unbound, or a
  constraint could not be evaluated.

`configuration` names the composed configuration, or is `None` for the root.
`generate ssp` records that name as `configuration` in the model SSP's
`extra/org.pyssp/selection.json`, and omits the key when it is absent.

A fixture pins the expected `legal` and `violated` names; the adapter computes
the partition, so the fixture keeps only its claim. Constraints come from the
effective members of a part definition, so a configuration is judged by the
asserted usages it inherits from its family, evaluated at the composed usage's
path.
