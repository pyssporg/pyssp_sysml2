"""Parameter dialect, synthesis, and variation resolution.

The dialect helpers live one module per layer under
``pyssp_sysml2.parameters.dialect``: ``markers``, ``declarations``,
``composition``, and ``mapping``. Callers import from the precise layer, for
example ``from pyssp_sysml2.parameters.dialect.mapping import mapping_specs``.
SSD-to-SysML synthesis (``synthesis``) and variation selection (``variation``)
stay in this package; there is no flat re-export surface.
"""
