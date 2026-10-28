"""SSP and FMI artifact generation.

Each module owns one artifact: SSD, SSV, SSM, SSP, FMI model descriptions, or
the study descriptor. They consume the repo-owned model and metadata layers and
do not parse SysML themselves.
"""
