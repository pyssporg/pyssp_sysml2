from __future__ import annotations

import re
from pathlib import Path

FIXED_GENERATION_TIME = "2000-00-00T00:00:00Z"
GEN_TIME_PATTERN = re.compile(r'generationDateAndTime="[^"]*"')


def normalize_generation_time(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    normalized = GEN_TIME_PATTERN.sub(
        f'generationDateAndTime="{FIXED_GENERATION_TIME}"',
        text,
    )
    if normalized != text:
        path.write_text(normalized, encoding="utf-8")

