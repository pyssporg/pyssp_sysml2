---
id: INFO-045
type: info
title: SSD parameter connectors
summary: Interface members become parameter connectors, and list members expand to one indexed connector each.
date: 2026-11-05
status: current
---

# SSD parameter connectors

Parameter connectors come from the component's interface.

- A member `attribute waypointCount : Integer;` becomes
  `<ssd:Connector name="waypointCount" kind="parameter"><ssc:Integer /></ssd:Connector>`.
- A list member `Real[3]` becomes three connectors `name[0]`, `name[1]`, and
  `name[2]`.
- Connectors sit on the component that owns the interface, not on the
  composition root.
- A nested system keeps its own connectors; its interface becomes system
  connectors at that level.
- The connector name is the interface member name, so a dotted name is
  rejected (`INFO-052`).
