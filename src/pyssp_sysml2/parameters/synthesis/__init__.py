"""SSD-to-SysML parameter synthesis, one module per pipeline stage.

``inputs`` reads the SSD, SSV, and SSM inputs; ``interfaces`` builds the
component parameter surfaces; ``application`` resolves bindings into set
applications; and ``generation`` emits the parameter sets and holds
``synthesize_parameter_dialect``. Import from the precise stage module; there
is no flat re-export surface.
"""
