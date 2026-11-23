"""Add the tracks, vias and ground plane in electrical/out/routes.json to the board.
Runs with KiCad's own Python, like pcb_build.py."""
import json
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parents[1]
routes = json.loads((HERE / "out" / "routes.json").read_text())
path = str(HERE / "kicad" / "manent.kicad_pcb")
board = pcbnew.LoadBoard(path)
mm = pcbnew.FromMM
pt = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))
n = routes["layers"]
assert board.GetCopperLayerCount() == n
LAYER = [pcbnew.F_Cu] + [getattr(pcbnew, f"In{i}_Cu") for i in range(1, n - 1)] + [pcbnew.B_Cu]

for t in routes["tracks"]:
    net = board.FindNet(t["net"])
    for a, b in zip(t["pts"], t["pts"][1:]):
        seg = pcbnew.PCB_TRACK(board)
        seg.SetStart(pt(*a)), seg.SetEnd(pt(*b))
        seg.SetWidth(mm(routes["track"])), seg.SetLayer(LAYER[t["layer"]]), seg.SetNet(net)
        board.Add(seg)

for v in routes["vias"]:
    via = pcbnew.PCB_VIA(board)
    l1, l2 = v["l1"], v["l2"]
    if (l1, l2) == (0, n - 1):
        kind = pcbnew.VIATYPE_THROUGH
    elif l2 - l1 == 1:
        kind = pcbnew.VIATYPE_MICROVIA
    else:
        kind = pcbnew.VIATYPE_BLIND if l1 == 0 or l2 == n - 1 else pcbnew.VIATYPE_BURIED
    via.SetViaType(kind)
    via.SetLayerPair(LAYER[l1], LAYER[l2])
    via.SetPosition(pt(v["x"], v["y"]))
    via.SetWidth(pcbnew.F_Cu, mm(routes["via_pad"]))
    via.SetDrill(mm(routes["via_drill"]))
    via.SetNet(board.FindNet(v["net"]))
    board.Add(via)

# Ground plane on the first flex layer, from one end of the strip to the other.
zone = pcbnew.ZONE(board)
zone.SetLayer(LAYER[routes["plane"]["layer"]])
zone.SetNet(board.FindNet(routes["plane"]["net"]))
zone.SetLocalClearance(mm(routes["clearance"]))
zone.SetMinThickness(mm(routes["track"]))
zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
outline = zone.Outline()
outline.NewOutline()
# The strip only: the test tail is cut off, so the plane stays out of it.
board_json = json.loads((HERE / "out" / "board.json").read_text())
half = board_json["width"] / 2
for x, y in ((0, -half), (board_json["length"], -half), (board_json["length"], half), (0, half)):
    outline.Append(mm(x), mm(y))
board.Add(zone)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())

pcbnew.SaveBoard(path, board)
print(f"{len(routes['tracks'])} tracks, {len(routes['vias'])} vias, ground plane on layer {routes['plane']['layer'] + 1}")
