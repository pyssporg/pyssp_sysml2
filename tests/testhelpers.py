from __future__ import annotations

from pathlib import Path

from pyssp_standard import SSD


COMPOSITION_NAME = "SystemComposition"


def write_model(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def write_bootstrap_ssd(path: Path, composition_name: str = COMPOSITION_NAME) -> Path:
    with SSD(path, mode="w") as ssd:
        top = ssd.new_system(composition_name)
        ssd.rename(composition_name)

        src = top.add_component("src", source="resources/Source.fmu")
        src.add_connector(name="outSig.x", kind="output", type_name="Real")
        src.add_connector(name="outSig.y", kind="output", type_name="Real")

        dst = top.add_component("dst", source="resources/Sink.fmu")
        dst.add_connector(name="inSig.x", kind="input", type_name="Real")
        dst.add_connector(name="inSig.y", kind="input", type_name="Real")

        top.add_connection(
            start_element="src",
            start_connector="outSig.x",
            end_element="dst",
            end_connector="inSig.x",
        )
        top.add_connection(
            start_element="src",
            start_connector="outSig.y",
            end_element="dst",
            end_connector="inSig.y",
        )

    return path
