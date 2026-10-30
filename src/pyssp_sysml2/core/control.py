"""Control-attribute names shared by the SysML/SSD adapters.

SSD metadata that has no first-class SysML v2 equivalent is carried as
ordinary ``pyssp_*`` attributes. Every generator skips them as model data.
Keeping the names in one tiny module avoids import cycles between the model
adapter, the parameter layer, and the SSD-to-SysML synthesis layer.
"""

from __future__ import annotations

CONTROL_PREFIX = "pyssp_"
DEFAULT_START_ATTR = f"{CONTROL_PREFIX}default_start_time"
DEFAULT_STOP_ATTR = f"{CONTROL_PREFIX}default_stop_time"
FLAT_CONNECTOR_ATTR = f"{CONTROL_PREFIX}flat_connector"
SELECTION_ATTR = f"{CONTROL_PREFIX}selection"

# Removed control attributes. They still match the pyssp_ prefix, so
# generators would otherwise skip them silently; validation turns them into
# migration errors instead.
RETIRED_CONTROL_ATTRS = {
    f"{CONTROL_PREFIX}implementation": (
        "use 'attribute fmu_meta : <Part>FmuMetadata { attribute "
        "implementation = \"...\"; }'"
    ),
    f"{CONTROL_PREFIX}parameter_set": (
        "define an 'attribute def <Set> :> ParameterSet' and bind it to the "
        "component with 'bind'"
    ),
}


def is_control_attribute(name: str) -> bool:
    return name.startswith(CONTROL_PREFIX)
