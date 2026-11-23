"""Write the exact copper of every pad on the board to electrical/out/pads.json.
Runs with KiCad's own Python, like pcb_build.py."""
import json
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parents[1]
board = pcbnew.LoadBoard(str(HERE / "kicad" / "manent.kicad_pcb"))
mm = pcbnew.ToMM
pads = []
for fp in board.GetFootprints():
    for pad in fp.Pads():
        pos = pad.GetPosition()
        entry = {"ref": fp.GetReference(), "pad": pad.GetNumber(), "net": pad.GetNetname(),
                 "x": mm(pos.x), "y": mm(pos.y)}
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            entry.update(kind="hole", d=mm(pad.GetDrillSize().x))
            pads.append(entry)
            continue
        layer = pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
        if not pad.IsOnLayer(layer):
            continue                      # paste-only apertures
        poly = pcbnew.SHAPE_POLY_SET()
        pad.TransformShapeToPolygon(poly, layer, 0, pcbnew.FromMM(0.002), pcbnew.ERROR_INSIDE)
        rings = []
        for i in range(poly.OutlineCount()):
            for line in [poly.Outline(i)] + [poly.Hole(i, h) for h in range(poly.HoleCount(i))]:
                rings.append([[mm(line.CPoint(k).x), mm(line.CPoint(k).y)] for k in range(line.PointCount())])
        entry.update(kind="pad", side="F" if layer == pcbnew.F_Cu else "B", rings=rings)
        pads.append(entry)
edge = []
for d in board.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts:
        edge.append([mm(d.GetStart().x), mm(d.GetStart().y), mm(d.GetEnd().x), mm(d.GetEnd().y)])
(HERE / "out" / "pads.json").write_text(json.dumps({"pads": pads, "edge": edge}))
print(len(pads), "pads and holes,", len(edge), "outline segments")
