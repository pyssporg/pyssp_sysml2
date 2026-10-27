---
id: INFO-010
type: info
title: SSD artifact
summary: generate ssd writes structure, parameter connectors, bindings, and default experiment without embedding values.
date: 2026-10-23
status: current
---

# SSD artifact

```bash
pyssp generate ssd \
  --architecture examples/parameter_sets \
  --composition AircraftComposition \
  --output build/generated/SystemStructure.ssd
```

## Structure

- A leaf part definition becomes an `ssd:Component`.
- A part definition with subparts becomes a nested `ssd:System`.
- The part usage name becomes the SSD element name.
- The part definition name determines `resources/<Definition>.fmu` for a leaf
  that declares `fmu_meta.source`.
- A leaf without `fmu_meta.source` gets an empty `Component/@source`.
- `fmu_meta.implementation` sets `Component/@implementation`.
- Connections are written per system level.

## Parameter connectors

Parameter connectors come from the interface. A member
`attribute waypointCount : Integer;` becomes
`<ssd:Connector name="waypointCount" kind="parameter"><ssc:Integer /></ssd:Connector>`.
A list member `Real[3]` becomes three connectors `name[0]`, `name[1]`, and
`name[2]`.

## Parameter bindings

An identity bind `bind autopilot.parameters = nominal;` becomes a
`ParameterBinding` with `source="parameter_sets/NominalSet.ssv"` and
`prefix="autopilot."`.

An explicit bind becomes a `ParameterBinding` with an inline
`ssm:ParameterMapping` and `MappingEntry` rows. The source path prefix is
controlled by `--parameter-set-prefix`, default `parameter_sets`.

Multiple disjoint sets produce multiple `ParameterBinding` entries at the top
system level. Nested targets use hierarchical names such as
`target="outer.inner.k"`. The binding still sits at the top system level, not
inside `outer`.

## Default experiment

Composition control attributes become:

```xml
<ssd:DefaultExperiment startTime="0" stopTime="3600" />
```

## Top-level restriction

`generate ssd` rejects a parameter interface on the top composition:

```text
Top-level composition parameter interfaces are not supported;
attach parameter interfaces to component usages
```
