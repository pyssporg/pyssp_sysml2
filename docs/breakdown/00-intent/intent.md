---
id: INFO-001
type: info
title: Intent
summary: Why pyssp_sysml2 exists: it turns a SysML v2 architecture into SSP-family artifacts and back, and owns nothing else.
date: 2026-11-05
status: current
---

# Intent

`pyssp_sysml2` turns a SysML v2 architecture model into the standard artifacts a
simulation workflow consumes, and turns those artifacts back into SysML. It owns
SSP-family emission and the SSD-to-SysML direction; it does not parse SysML,
generate FMI, run, or judge.

It covers two directions:

- SysML architecture or SSD to SSD, one SSV per parameter set, SSM parameter
  mappings, an analysis descriptor, and a packaged SSP.
- SSD wiring edits synced back into an existing SysML composition, or a minimal
  SysML architecture synthesized from an SSD.

Scope is `INFO-028`, commitments `INFO-029`, non-goals `INFO-030`, and package
roles `INFO-031`.
