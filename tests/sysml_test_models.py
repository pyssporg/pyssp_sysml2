from __future__ import annotations

from pathlib import Path


COMPOSITION_NAME = "SystemComposition"


def write_model(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def write_connected_triplet_architecture(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)

    write_model(
        root / "ports.sysml",
        """
        package Example {
          port def Cmd {
            attribute pitch: Real;
            attribute mode: Integer;
          }

          port def Pos {
            attribute x: Real;
            attribute y: Real;
          }
        }
        """,
    )

    write_model(
        root / "parts.sysml",
        """
        package Example {
          part def A {
            attribute gains = [1.0, 2.0, 3.0];
            out port cmd : Cmd;
          }

          part def B {
            in port cmdIn : Cmd;
            out port pos : Pos;
          }

          part def C {
            in port posIn : Pos;
          }
        }
        """,
    )

    write_model(
        root / "composition.sysml",
        f"""
        package Example {{
          part def {COMPOSITION_NAME} {{
            part a : A;
            part b : B;
            part c : C;

            connect a.cmd to b.cmdIn;
            connect b.pos to c.posIn;
          }}
        }}
        """,
    )

    return root
