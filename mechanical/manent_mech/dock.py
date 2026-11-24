"""The charging dock: a post the ring slides onto, three spring pins, two magnets.

Coordinates of the dock: Z is the post's axis, the ring rests on the base at z = 0, the row of
pins looks along +X. One dock is printed per ring size; see docs/charging.md.
"""
import math

from . import stack as S
from .checks import arc_report, best_cell, contacts_report
from .params import ENVELOPES, RingParams

PLAY = 0.5             # post smaller than the ring's bore by this much, on the diameter
PIN_HOLE = 1.05        # bore for a spring pin with a 1.0 body
PIN_TIP = 0.4          # widest tip allowed: it must not bridge two contacts
PIN_OUT = 0.8          # how far a free pin stands out of the post; pressed in by PIN_OUT - PLAY at least
MAGNET = (2.1, 4.3, 3.0)   # pocket: along the arc, along the axis, deep. Two 2 x 3 discs or one block
MAGNET_AT = 1.9        # centre of each magnet pocket from the row of pins, along the arc
SKIN = 0.4             # plastic left between a magnet and the ring
BORE = 8.0             # hollow middle of the post, for the wires
HEAD = 2.5             # post above the top edge of the ring
BASE_T, BASE_RIM = 6.0, 7.0
MIN_WALL = 0.3         # thinnest printed wall accepted


def dock_report(p: RingParams, parts, key: str = "B") -> dict:
    con = contacts_report(p, parts)
    charge = [s for s in con["slugs"] if s["pad"].startswith("charge")]
    post_d = p.inner_diameter_min - PLAY
    where = {w["island"]: w["centre_deg"] for w in arc_report(p, parts, best_cell(p, parts) or S.DEFAULT_CELL[key])["placed"]}
    row_deg = where["contacts"] + math.degrees(con["row_x"] / con["plane_radius"])
    pitch = min(abs(a["y"] - b["y"]) for a in charge for b in charge if a is not b)
    walls = {"between pins": pitch - PIN_HOLE,
             "pin to magnet": MAGNET_AT - MAGNET[0] / 2 - PIN_HOLE / 2,
             "behind a magnet": (post_d - BORE) / 2 - SKIN - MAGNET[2]}
    kl = S.KEEPER[0]
    covered = max(0.0, min(kl / 2, MAGNET_AT + MAGNET[0] / 2) - (MAGNET_AT - MAGNET[0] / 2)) / MAGNET[0]
    slug_d = min(s["diameter"] for s in charge)
    # the pockets open into the bore, so "behind a magnet" only has to be positive: the magnet is all inside the wall
    problems = [f"wall {k} is {v:.2f}" for k, v in walls.items() if v < (0 if k == "behind a magnet" else MIN_WALL)]
    if PIN_TIP >= con["closest_pair"]:
        problems.append("a pin tip can bridge two contacts")
    if PIN_OUT <= PLAY:
        problems.append("the pins do not reach a ring pushed to the far side")
    return {"us_size": round(p.us_size, 2), "post_diameter": round(post_d, 2), "post_height": p.band_width + HEAD,
            "pin_z": [round(p.half_width + s["y"], 2) for s in sorted(charge, key=lambda s: s["y"])],
            "pin_pitch": pitch, "pin_pressed_by": round(PIN_OUT - PLAY, 2),
            # how far the ring may be turned from true before a pin tip leaves its contact, at the bore
            "turn_tolerance_deg": round(math.degrees((slug_d - PIN_TIP) / 2 / (p.inner_diameter_min / 2)), 1),
            "button_from_pins_deg": round(where["button"] - row_deg, 1),
            "magnet_to_keeper": round(con["keeper"]["behind_surface"] + SKIN, 2),
            "magnet_under_keeper": round(covered, 2),
            "walls": {k: round(v, 2) for k, v in walls.items()}, "ok": not problems, "problems": problems}


def build(key: str = "B", us_size: float | None = None):
    """The dock as one printable body."""
    from build123d import Box, Cylinder, Pos, Rot, chamfer, Axis
    p = ENVELOPES[key] if us_size is None else ENVELOPES[key].for_size(us_size)
    rep = dock_report(p, S.load_parts(), key)
    rp, h = rep["post_diameter"] / 2, rep["post_height"]
    r_base = p.outer_diameter / 2 + BASE_RIM
    post = Pos(0, 0, h / 2) * Cylinder(rp, h)
    post = chamfer(post.edges().group_by(Axis.Z)[-1], 1.0)
    body = Pos(0, 0, -BASE_T / 2) * Cylinder(r_base, BASE_T) + post
    body -= Pos(0, 0, (h - BASE_T) / 2) * Cylinder(BORE / 2, h + BASE_T + 1)         # wires
    body -= Pos(0, 0, -BASE_T + 1.5) * Box(22, 12, 3.0)                              # USB-C board, from below
    body -= Pos(r_base / 2 + 5, 0, -BASE_T + 1.5) * Box(r_base, 9.5, 3.0)             # its socket, to the edge
    radial = Rot(0, 90, 0)
    for z in rep["pin_z"]:
        body -= Pos(rp / 2 + 1, 0, z) * radial * Cylinder(PIN_HOLE / 2, rp)
    depth = rp - SKIN - BORE / 2 + 0.5
    for side in (-1, 1):                                                             # pockets open into the bore
        body -= (Rot(0, 0, side * math.degrees(MAGNET_AT / rp))
                 * Pos(rp - SKIN - depth / 2, 0, p.half_width) * Box(depth, MAGNET[0], MAGNET[1]))
        # where the button must stop: one groove for each way round the ring can go on
        body -= (Rot(0, 0, side * rep["button_from_pins_deg"])
                 * Pos(p.outer_diameter / 2 + 1.0 + 2.0, 0, 0) * Box(4.0, 0.8, 1.2))
    return body


if __name__ == "__main__":
    from build123d import export_stl
    out, parts = S.ROOT / "mechanical" / "out", S.load_parts()
    for size in S.SIZES:
        rep = dock_report(ENVELOPES["B"].for_size(size), parts)
        export_stl(build("B", size), str(out / f"print-dock-US{size}.stl"))
        print(f"US {size}: post {rep['post_diameter']} x {rep['post_height']}, button {rep['button_from_pins_deg']} deg from the pins, "
              f"turn tolerance +/-{rep['turn_tolerance_deg']} deg  {'ok' if rep['ok'] else 'FAIL ' + '; '.join(rep['problems'])}")
    print("print-dock-US*.stl written")
