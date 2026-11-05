---
title: Operation
summary: How authors set up, run the CLI, validate examples, troubleshoot, migrate to 0.4, and write docs.
---

# Operation

Routine setup, CLI use, example validation, troubleshooting, migration, and
documentation authoring.

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **INFO-020** [Local setup](local-setup.md) — Create a virtual environment, install the two direct-URL dependencies, and install the package editable; sysmlpy is transitive.
- **INFO-021** [CLI usage](cli-and-examples.md) — The pyssp entry point exposes generate and sync subcommands; generate fmi was removed and names pyfmi_sysml2 in its error.
- **INFO-022** [Troubleshooting](troubleshooting.md) — Missing console script, dependency resolution, generate fmi, and SSD shape failures have direct fixes.
- **INFO-023** [Documentation authoring rules](documentation-authoring.md) — Documented rules need a runnable example, an explicit status, the SSP consequence, and a source-of-truth pointer.
- **INFO-057** [Runnable examples](examples.md) — cli_usage.sh and module_usage.py walk the CLI and Python API, and examples/parameter-sets holds four dialect models.
- **INFO-058** [Migration to 0.4](migration-to-0.4.md) — v0.4.0 moved the SysML dialect to pycps_sysml2 and FMI to pyfmi_sysml2, kept one minor of import shims, and changed flat-connector semantics.
<!-- pb:index:end -->
