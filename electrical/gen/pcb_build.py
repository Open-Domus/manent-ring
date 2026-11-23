"""Build electrical/kicad/manent.kicad_pcb from electrical/out/board.json.

Runs with KiCad's own Python (the pcbnew module), not the project environment:
    python3 gen/pcb_build.py          (from the electrical directory)
Footprints are placed and their pads given their nets. Tracks come later, from
pcb_route.py.
"""
import json
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parents[1]
data = json.loads((HERE / "out" / "board.json").read_text())
lib = str(HERE / "kicad" / (data["lib"] + ".pretty"))
mm = pcbnew.FromMM
pt = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))

board = pcbnew.BOARD()
board.SetCopperLayerCount(data["layers"])
board.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(data["thickness"]))
nets = {}
for part in data["parts"]:
    for name in part["nets"].values():
        if name not in nets:
            nets[name] = pcbnew.NETINFO_ITEM(board, name)
            board.Add(nets[name])

for part in data["parts"]:
    fp = pcbnew.FootprintLoad(lib, part["footprint"])
    assert fp is not None, part["footprint"]
    fp.SetFPID(pcbnew.LIB_ID(data["lib"], part["footprint"]))
    fp.SetReference(part["ref"])
    fp.SetValue(part["value"])
    fp.SetPath(pcbnew.KIID_PATH(part["path"]))
    fp.SetDNP(part["dnp"])
    for key, value in part["fields"].items():
        fp.SetField(key, value)
        fp.GetField(key).SetVisible(False)
    board.Add(fp)
    fp.SetPosition(pt(part["x"], part["y"]))
    fp.SetOrientationDegrees(part["rot"])
    if part["side"] == "B":
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    for pad in fp.Pads():
        net = part["nets"].get(pad.GetNumber())
        if net:
            pad.SetNet(nets[net])


def line(a, b, layer, width=0.05):
    s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pt(*a)), s.SetEnd(pt(*b)), s.SetLayer(layer), s.SetWidth(mm(width))
    board.Add(s)


def note(text, x, y, layer, size=0.5):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text), t.SetPosition(pt(x, y)), t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size))), t.SetTextThickness(mm(size / 6))
    board.Add(t)


outline = data["outline"]
for a, b in zip(outline, outline[1:] + outline[:1]):
    line(a, b, pcbnew.Edge_Cuts)
half = data["width"] / 2
for z in data["zones"]:
    for x in (z["x0"], z["x1"]):
        line((x, -half), (x, half), pcbnew.Dwgs_User, 0.03)
    # On the drawing layer, which goes to the fabricator with the Gerber files.
    note("FLEX" if z["kind"] == "bend" else f'RIGID: {z["name"]}',
         (z["x0"] + z["x1"]) / 2, -half - 0.6 - (0.7 if z["kind"] == "bend" else 0), pcbnew.Dwgs_User, 0.4)
x0, x1, y = data["tail_cut"]
line((x0, y), (x1, y), pcbnew.Dwgs_User, 0.08)
note("cut here after test", x1 + 2.6, y + 0.6, pcbnew.Dwgs_User, 0.4)
note("Top copper faces the titanium, bottom copper faces the finger.",
     data["length"] / 2, -half - 2.4, pcbnew.Dwgs_User, 0.5)

out = HERE / "kicad" / "manent.kicad_pcb"
pcbnew.SaveBoard(str(out), board)
print(f"{len(data['parts'])} footprints, {len(nets)} nets -> {out.name}")
