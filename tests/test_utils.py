from __future__ import annotations

from pathlib import Path


COMPOSITION_NAME = "SystemComposition"


def write_model(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
