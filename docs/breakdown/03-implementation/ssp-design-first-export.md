---
id: INFO-048
type: info
title: SSP design-first export
summary: A leaf with no source exports without a flag, a declared but unbuilt source needs allow-missing-fmus, and attach_fmu populates later.
date: 2026-11-05
status: current
---

# SSP design-first export

A leaf with no `fmu_meta.source`, or no metadata at all, is exported without a
flag. Its SSD component and connectors are written, its `source` is empty, no
resource is packaged, and FMU validation skips it. A warning names each such
component.

A declared source that is not on disk is an error unless `--allow-missing-fmus`
is passed. In that case the component keeps `resources/<PartDefinition>.fmu` as
its source and no resource is packaged. Present FMUs are still packaged and
validated.

The result is a structurally complete design artifact, not a runnable SSP.
Populate it with built binaries:

```python
from pyssp_standard import SSP

with SSP("build/design.ssp", mode="a") as ssp:
    ssp.attach_fmu("source", "build/CsvSource.fmu")
    ssp.validate_fmu_interfaces()
```

`attach_fmu` copies the FMU into `resources/`, points the component's `source`
at it, and checks connector names, connector kinds, and implementation. A
populated archive is an ordinary SSP: it can be simulated, reopened, or
unpacked.
