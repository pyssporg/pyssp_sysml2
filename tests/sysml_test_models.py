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
            in port cmdIn : Cmd;
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


def write_ssv_type_coverage_architecture(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)

    write_model(
        root / "parts.sysml",
        f"""
        package Example {{
          part def Params {{
            attribute r = 1.5;
            attribute i = 7;
            attribute b = true;
            attribute s = "abc";
            attribute i_list = [1, 2];
            attribute b_list = [True, False];
          }}

          part def {COMPOSITION_NAME} {{
            part p : Params;
          }}
        }}
        """,
    )

    return root


def write_fmi_list_type_architecture(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)

    write_model(
        root / "ports.sysml",
        """
        package Example {
          port def Status {
            attribute ok: Boolean;
          }
        }
        """,
    )

    write_model(
        root / "parts.sysml",
        f"""
        package Example {{
          part def Comp {{
            attribute int_list = [1, 2];
            attribute bool_list = [True, False];
            out port status : Status;
          }}

          part def {COMPOSITION_NAME} {{
            part c : Comp;
          }}
        }}
        """,
    )

    return root
