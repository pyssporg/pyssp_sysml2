"""Common SSP namespace helpers shared by SSD generators."""
from __future__ import annotations

import xml.etree.ElementTree as ET

SSD_NAMESPACE = "http://ssp-standard.org/SSP1/SystemStructureDescription"
SSC_NAMESPACE = "http://ssp-standard.org/SSP1/SystemStructureCommon"
SSV_NAMESPACE = "http://ssp-standard.org/SSP1/SystemStructureParameterValues"
SSM_NAMESPACE = "http://ssp-standard.org/SSP1/SystemStructureParameterMapping"
SSB_NAMESPACE = "http://ssp-standard.org/SSP1/SystemStructureSignalDictionary"
OMS_NAMESPACE = "https://raw.githubusercontent.com/OpenModelica/OMSimulator/master/schema/oms.xsd"

SSP_NAMESPACES = {
    "ssd": SSD_NAMESPACE,
    "ssc": SSC_NAMESPACE,
    "ssv": SSV_NAMESPACE,
    "ssm": SSM_NAMESPACE,
    "ssb": SSB_NAMESPACE,
    "oms": OMS_NAMESPACE,
}


def register_ssp_namespaces() -> None:
    """Register the standard SSP XML namespaces with ElementTree."""
    for prefix, uri in SSP_NAMESPACES.items():
        ET.register_namespace(prefix, uri)
