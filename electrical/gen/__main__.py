from pathlib import Path

from .design import SHEETS, build
from .emit import write_project

out = Path(__file__).resolve().parents[1] / "kicad"
comps = build()
write_project(out, comps, SHEETS)
print(f"{len(comps)} components on {len(SHEETS)} sheets -> {out}")
