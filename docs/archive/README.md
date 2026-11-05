<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->

# Decision Stream

Flat, dated history of every committed design choice. Current state lives
in the layer leaves named by each record's `state:` field.

Records live in the cold-storage archive; extract one with `pb archive read <ID>`.

## By Layer

### Architecture

- **AD-001** — Constraints Are Captured in the Adapter and Evaluated After Selection · accepted · 2026-10-30 · `AD-001`
  Constraint definitions and asserted usages are repo-owned model data, evaluated after variation selection and before artifact writes.
- **AD-002** — Analyses Declare Their Variation Selection with a Control Attribute · accepted · 2026-10-30 · `AD-002`
  A pyssp_selection control attribute on an Analysis is the single authored selection; the adapter resolves it and classifies each analysis as legal, violated, or invalid.
- **AD-003** — Configurations derive the analysis selection · accepted · 2026-10-30 · `AD-003`
  An analysis composes a model-level SysML v2 configuration; the adapter derives the selection map from its redefinitions and feature values, replacing the pyssp_selection control attribute.

### Implementation

- **AD-004** — pyssp_sysml2 Becomes an SSP-Artifact Implementer · accepted · 2026-11-05 · `AD-004`
  At v0.4.0 pyssp_sysml2 keeps only SSP-family emission and SSD-to-SysML synthesis; the SysML dialect moved to pycps_sysml2 and FMI to pyfmi_sysml2.
