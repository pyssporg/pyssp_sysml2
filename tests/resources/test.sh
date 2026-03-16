#!/usr/bin/env bash

pyssp generate sysml \
  --ssd tests/resources/embrace.ssd \
  --output build/generated/architecture_v1.sysml

  pyssp generate sysml \
  --ssd tests/resources/openscaling.ssd \
  --output build/generated/architecture_v2.sysml

  pyssp generate ssd \
  --architecture build/generated/architecture_v1.sysml \
  --composition root \
  --output build/generated/SystemStructure_export.ssd \
  --skip_type_check