---
id: INFO-049
type: info
title: Validation of parameter ports and mixing
summary: A part has at most one parameters port, may not declare flat parameter attributes, and cannot be the composition root.
date: 2026-11-05
status: current
---

# Validation of parameter ports and mixing

- At most one `parameters` port per part. A duplicate is a model error; rename
  or remove the extra port.
- A part may not declare flat parameter attributes. The diagnostic says
  `... is a flat parameter attribute, which is no longer supported`.
- A composition may not declare flat parameter attributes.
- The composition root is not a parameter target. The diagnostic says
  `Top-level composition parameter interfaces are not supported`.
- A synthesized parameter port cannot reuse a subpart name. The diagnostic says
  `already has a subpart named 'parameters'`.
- The port is `in port parameters : <Interface>;`; flat attributes are retired
  and rejected.
