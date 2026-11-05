---
id: IMP-016
type: imp
title: FMI Model Exchange and FMI 3.0 ownership
summary: After the v0.4.0 split, pyfmi_sysml2 owns FMI 2.0 Co-Simulation packaging but no package owns Model Exchange or FMI 3.0.
date: 2026-11-05
status: suggested
---

# FMI Model Exchange and FMI 3.0 ownership

After the v0.4.0 split, FMI belongs to `pyfmi_sysml2` 0.1.0. Its scope covers
FMI 2.0 model descriptions, C headers, Modelica connectors, and FMU packaging.

Two FMI capabilities have no owner:

- **Model Exchange**: states, derivatives, and event indicators in the model
  description, plus the ME calling sequence.
- **FMI 3.0**: the 3.0 schema, terminals, clocks, and the variable-type changes
  that replace the 2.0 `ScalarVariable` shape.

**Candidate.**

- Decide whether `pyfmi_sysml2` extends its FMI 2.0 surface or a separate
  package owns ME and 3.0.
- Keep the SSP side unchanged: `pyssp_sysml2` packages whatever `.fmu` file a
  leaf declares, regardless of FMI version (`INFO-012`).
- Do not reintroduce FMI emission into `pyssp_sysml2`; the boundary is
  deliberate (`AD-004`, `INFO-031`).

**Open questions.**

- Which FMI version does the simulation workflow need first?
- Does a Model Exchange FMU share the same packaging and validation path?
- Is a version-specific modelDescription a contract change for the goldens?
