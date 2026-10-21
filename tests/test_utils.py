from __future__ import annotations

from pathlib import Path

from pyssp_standard.ssd import Component, Connection, Connector, SSD, System


COMPOSITION_NAME = "SystemComposition"


def write_model(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def write_bootstrap_ssd(path: Path, composition_name: str = COMPOSITION_NAME) -> Path:
    with SSD(path, mode="w") as ssd:
        ssd.xml.name = composition_name
        ssd.xml.version = "1.0"
        ssd.xml.system = System(name=composition_name)

        src = Component()
        src.name = "src"
        src.source = "resources/Source.fmu"
        src.connectors.extend(
            [
                Connector(name="outSig.x", kind="output", type_name="Real"),
                Connector(name="outSig.y", kind="output", type_name="Real"),
            ]
        )
        ssd.xml.system.elements.append(src)

        dst = Component()
        dst.name = "dst"
        dst.source = "resources/Sink.fmu"
        dst.connectors.extend(
            [
                Connector(name="inSig.x", kind="input", type_name="Real"),
                Connector(name="inSig.y", kind="input", type_name="Real"),
            ]
        )
        ssd.xml.system.elements.append(dst)

        ssd.xml.system.connections.extend(
            [
                Connection(
                    start_element="src",
                    start_connector="outSig.x",
                    end_element="dst",
                    end_connector="inSig.x",
                ),
                Connection(
                    start_element="src",
                    start_connector="outSig.y",
                    end_element="dst",
                    end_connector="inSig.y",
                ),
            ]
        )

    return path
