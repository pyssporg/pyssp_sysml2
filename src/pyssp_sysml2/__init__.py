"""SysML utilities package for architecture parsing and generation SSP."""

__version__ = "0.1.0"

from pyssp_sysml2.fmi import generate_model_descriptions
from pyssp_sysml2.ssd import build_ssd, generate_ssd
from pyssp_sysml2.ssv import generate_parameter_set
from pyssp_sysml2.sysml import generate_sysml_from_ssd
from pyssp_sysml2.sync import sync_sysml_from_ssd

__all__ = [
    "build_ssd",
    "generate_ssd",
    "generate_parameter_set",
    "generate_model_descriptions",
    "generate_sysml_from_ssd",
    "sync_sysml_from_ssd",
]
