"""Where every footprint goes on the flat board, written to electrical/out/board.json.

The board is the ring's circuit unrolled: X runs along the arc from the cell tabs, Y across
the band. The top copper faces the titanium, the bottom faces the finger. Positions come
from the fit model (mechanical/manent_mech/stack.py), so the board and the model agree.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from mechanical.manent_mech import stack as S

from .design import SHEETS, build
from .emit import uid
from .footprints import LIB_NAME, footprint_of

ROOT = Path(__file__).resolve().parents[2]
TAIL_W, TAIL_PITCH = 2.0, 1.27
RULES = {  # millimetres; a rigid-flex build with laser microvias
    # Hole clearance: a 0.1 mm laser hole in a 0.2 mm pad leaves 0.05 of ring; another net's copper
    # at the 0.075 clearance from that pad is 0.125 from the hole.
    "min_clearance": 0.075, "min_track_width": 0.075, "min_copper_edge_clearance": 0.15,
    "min_hole_clearance": 0.125, "min_hole_to_hole": 0.2, "min_through_hole_diameter": 0.1,
    "min_via_diameter": 0.2, "min_via_annular_width": 0.05, "min_microvia_diameter": 0.2,
    "min_microvia_drill": 0.1, "allow_blind_buried_vias": True, "allow_microvias": True,
}
LAYERS = 6            # copper layers on the rigid islands; the two in the middle are the flex
NET_CLASS = {"name": "Default", "clearance": 0.075, "track_width": 0.075, "via_diameter": 0.25, "via_drill": 0.1,
             "microvia_diameter": 0.2, "microvia_drill": 0.1, "diff_pair_width": 0.075, "diff_pair_gap": 0.075,
             "diff_pair_via_gap": 0.1, "wire_width": 6, "bus_width": 12, "line_style": 0,
             "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)"}
# Checks switched off on purpose. Stock courtyards assume hand rework room this board does
# not have; spacing is enforced instead by the packer in the fit model (0.15 mm between land
# patterns). There is no silkscreen on a potted ring.
IGNORED = ("courtyards_overlap", "silk_overlap", "silk_over_copper", "silk_edge_clearance", "text_height",
           "text_thickness", "lib_footprint_mismatch")


def unconnected_nets() -> dict[tuple[str, str], str]:
    """Names KiCad gave to the nets of no-connect pins, so the board can carry the same."""
    path = ROOT / "electrical" / "out" / "netlist.xml"
    out = {}
    for net in ET.parse(path).getroot().iter("net"):
        if net.get("name").startswith("unconnected-"):
            for node in net.iter("node"):
                out[(node.get("ref"), node.get("pin"))] = net.get("name")
    return out


def write_project():
    """Board rules live in the project file, next to the board."""
    path = ROOT / "electrical" / "kicad" / "manent.kicad_pro"
    pro = json.loads(path.read_text()) if path.exists() else {}
    pro.setdefault("meta", {"filename": "manent.kicad_pro", "version": 3})
    settings = pro.setdefault("board", {}).setdefault("design_settings", {})
    settings.setdefault("rules", {}).update(RULES)
    settings.setdefault("rule_severities", {}).update({k: "ignore" for k in IGNORED})
    pro.setdefault("net_settings", {})["classes"] = [NET_CLASS]
    path.write_text(json.dumps(pro, indent=2, sort_keys=True) + "\n")


def layout() -> dict:
    comps = {c.ref: c for c in build() if footprint_of(c)}
    half = S.FLEX_WIDTH / 2
    x, zones, placed, centre = S.CELL_TABS, [{"name": "cell tabs", "x0": 0.0, "x1": S.CELL_TABS, "kind": "tabs"}], {}, {}
    for isl in S.ISLANDS:
        zones.append({"name": "bend", "x0": x, "x1": x + S.BEND, "kind": "bend"})
        x += S.BEND
        centre[isl.name] = x + isl.length / 2
        zones.append({"name": isl.name, "x0": x, "x1": x + isl.length,
                      "kind": "rigid"})
        for pl in isl.parts:
            placed[pl.ref] = (centre[isl.name] + pl.x, pl.y, "F" if pl.face == "out" else "B", 90 if pl.turned else 0)
        x += isl.length
    length = round(x, 2)

    cell = next(r for r, c in comps.items() if c.sym.name == "CELL")
    placed[cell] = (1.3, 0.0, "F", 0)
    cx, charge_minus, tail = centre["contacts"], [-1.9, 1.9], 0
    for ref, c in comps.items():
        if c.sym.name != "PAD":
            continue
        if c.value == "charge +":
            placed[ref] = (cx - 0.6, 0.0, "B", 0)
        elif c.value == "charge -":
            placed[ref] = (cx - 0.6, charge_minus.pop(), "B", 0)
        elif c.value in ("SWDIO", "SWDCLK"):
            placed[ref] = (cx + 0.95, -1.0 if c.value == "SWDIO" else 1.0, "B", 0)
        else:
            placed[ref] = (centre["soc"], half + 1.0 + TAIL_PITCH * tail, "F", 0)
            tail += 1
    tail_len = 1.0 + TAIL_PITCH * (tail - 1) + 1.0
    xs = centre["soc"]
    outline = [(0, -half), (length, -half), (length, half), (xs + TAIL_W / 2, half), (xs + TAIL_W / 2, half + tail_len),
               (xs - TAIL_W / 2, half + tail_len), (xs - TAIL_W / 2, half), (0, half)]
    assert set(placed) == set(comps), sorted(set(comps) ^ set(placed))

    sheet = {name: uid("sheet", name) for name, _ in SHEETS}
    nc = unconnected_nets()
    parts = []
    for ref, c in comps.items():
        px, py, side, rot = placed[ref]
        parts.append({"ref": ref, "value": c.value, "footprint": footprint_of(c), "x": round(px, 4), "y": round(py, 4),
                      "side": side, "rot": rot, "dnp": c.dnp,
                      "path": f"/{sheet[c.sheet]}/{uid(c.sheet, ref)}",
                      "fields": {k: v for k, v in c.fields.items() if k not in ("Footprint", "Datasheet")},
                      "nets": {pin: net or nc[(ref, pin)] for pin, net in c.nets.items()}})
    return {"lib": LIB_NAME, "layers": LAYERS, "length": length, "width": S.FLEX_WIDTH, "outline": outline, "zones": zones,
            "tail_cut": [xs - TAIL_W / 2, xs + TAIL_W / 2, half], "rules": RULES, "parts": parts}


if __name__ == "__main__":
    data = layout()
    write_project()
    out = ROOT / "electrical" / "out" / "board.json"
    out.write_text(json.dumps(data, indent=1) + "\n")
    print(f"{len(data['parts'])} footprints on a board {data['length']} x {data['width']} mm -> {out.name}")
