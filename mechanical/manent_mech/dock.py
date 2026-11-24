"""The charging dock: a post the ring slides onto, with a sprung shoe that carries three
contact bars and a magnet.

The bars run along the arc, so the ring only has to be turned roughly the right way; the
first version had three spring pins, which asked for 3 degrees. See docs/charging.md.

Coordinates of the dock: Z is the post's axis, the ring rests on the base at z = 0, the shoe
looks along +X. One dock is printed per ring size.
"""
import math

from . import stack as S
from .checks import arc_report, best_cell, contacts_report
from .params import ENVELOPES, RingParams

PLAY = 0.5             # post smaller than the ring's bore by this much, on the diameter
BAR_D = 0.4            # contact bar: round wire laid along the arc, in a groove of the shoe
BAR_PROUD = 0.15       # how far a bar stands out of the shoe's face
BAR_HALF_ARC = 22.0    # each bar covers this many degrees either side of the middle
SHOE_T = 3.3           # shoe, radially
SHOE_H = 5.2           # shoe, along the axis: it must stay inside the resin window of the bore
SHOE_OUT = 0.8         # how far the free shoe's face stands out of the post
SHOE_GAP = 0.15        # printed clearance round the shoe in its slot
MAGNET = (4.0, 4.0, 2.0)   # one block behind the bars: along the arc, along the axis, thick
SHOE_FACE = 0.7        # plastic between the magnet and the shoe's face
SPRING = (2.2, 2.5)    # pocket for each of the two springs behind the shoe: bore, depth
BORE = 6.0             # hollow middle of the post, for the wires
HEAD = 2.5             # post above the top edge of the ring
BASE_T, BASE_RIM = 6.0, 7.0
SEAT = 0.25            # how far the ring may sit off its height on the post: clearances must beat it
BR = 1.3               # remanence of the magnet, tesla (N42)
MU0 = 4e-7 * math.pi


def field_on_axis(z: float, a: float, b: float, length: float) -> float:
    """Flux density in tesla at distance z (mm) in front of the a x b pole of a block magnet."""
    f = lambda d: math.atan(a * b / (2 * d * math.sqrt(4 * d * d + a * a + b * b)))
    return BR / math.pi * (f(z) - f(z + length))


def magnet_pull(distance: float) -> dict:
    """First-order pull of the magnet on the keeper: the field it would have there in air,
    doubled by the steel, as a pressure on the pole's area. Good to a factor of two at best."""
    a, b, length = MAGNET
    field = field_on_axis(distance, a, b, length)
    area = min(a, S.KEEPER[0]) * min(b, S.KEEPER[1])
    newton = (2 * field) ** 2 / (2 * MU0) * area * 1e-6
    # the keeper must carry that flux sideways through its own thickness without saturating (about 1.6 T)
    in_steel = 2 * field * area / (2 * (a + b) * S.KEEPER[2])
    return {"field_mT": round(field * 1000), "pull_N": round(newton, 2), "keeper_T": round(in_steel, 2)}


def dock_report(p: RingParams, parts, key: str = "B") -> dict:
    con = contacts_report(p, parts)
    charge = sorted((s for s in con["slugs"] if s["pad"].startswith("charge")), key=lambda s: s["y"])
    service = [s for s in con["slugs"] if not s["pad"].startswith("charge")]
    bore_r = p.inner_diameter_min / 2
    post_d = p.inner_diameter_min - PLAY
    where = {w["island"]: w["centre_deg"] for w in arc_report(p, parts, best_cell(p, parts) or S.DEFAULT_CELL[key])["placed"]}
    row_deg = where["contacts"] + math.degrees(con["row_x"] / con["plane_radius"])
    # A bar passes over everything on its circle: it must miss the service contacts and the
    # neighbouring charging contact, even with the ring seated a little high or low.
    to_service = min(abs(abs(v["y"]) - abs(c["y"])) - v["diameter"] / 2 - BAR_D / 2 for v in service for c in charge)
    to_next = min(abs(a["y"] - b["y"]) - b["diameter"] / 2 - BAR_D / 2 for a in charge for b in charge if a is not b)
    to_titanium = min(s["to_titanium"] + s["diameter"] / 2 - BAR_D / 2 for s in charge)
    slug_deg = math.degrees(charge[0]["diameter"] / 2 / bore_r)
    magnet_to_keeper = con["keeper"]["behind_surface"] + BAR_PROUD + SHOE_FACE
    pull = magnet_pull(magnet_to_keeper)
    walls = {"under a bar's groove": SHOE_FACE - (BAR_D - BAR_PROUD),
             "shoe to the resin window": (p.half_width - p.corner_r) - SHOE_H / 2,
             "post behind the shoe": post_d / 2 - (SHOE_T - SHOE_OUT + SHOE_GAP) - SPRING[1] - BORE / 2,
             "bar to a service contact": to_service - SEAT, "bar to the next contact": to_next - SEAT,
             "bar to the titanium": to_titanium - SEAT}
    problems = [f"{k}: {v:.2f}" for k, v in walls.items() if v < 0.05]
    if SHOE_OUT <= PLAY:
        problems.append("the shoe does not reach a ring pushed to the far side")
    return {"us_size": round(p.us_size, 2), "post_diameter": round(post_d, 2), "post_height": p.band_width + HEAD,
            "bar_z": [round(p.half_width + s["y"], 2) for s in charge], "bar_radius": round(bore_r - BAR_D / 2, 2),
            "shoe_pressed_by": round(SHOE_OUT - PLAY, 2),
            # how far the ring may be turned from true with its contact still wholly on the bar
            "turn_tolerance_deg": round(BAR_HALF_ARC - slug_deg, 1),
            "turn_tolerance_at_button_mm": round(math.radians(BAR_HALF_ARC - slug_deg) * p.outer_diameter / 2, 1),
            "button_from_bars_deg": round(where["button"] - row_deg, 1),
            "magnet_to_keeper": round(magnet_to_keeper, 2), "magnet": pull,
            "margins": {k: round(v, 2) for k, v in walls.items()}, "ok": not problems, "problems": problems}


def build(key: str = "B", us_size: float | None = None):
    """The dock as two printable bodies: base with post, and the shoe that goes in its slot."""
    from build123d import Axis, Box, Cylinder, Pos, Rot, Torus, chamfer
    p = ENVELOPES[key] if us_size is None else ENVELOPES[key].for_size(us_size)
    rep = dock_report(p, S.load_parts(), key)
    rp, h, zc = rep["post_diameter"] / 2, rep["post_height"], p.half_width
    r_base = p.outer_diameter / 2 + BASE_RIM
    radial = Rot(0, 90, 0)

    def sector(r_in, r_out, half_deg, height):
        """Part of a tube: the piece within half_deg of +X."""
        big = 4 * r_out
        tube = Cylinder(r_out, height) - Cylinder(r_in, height + 1) - Pos(-big / 2, 0, 0) * Box(big, 2 * big, height + 1)
        for side in (-1, 1):
            tube -= Rot(0, 0, side * half_deg) * Pos(0, side * big / 2, 0) * Box(2 * big, big, height + 1)
        return tube

    post = Pos(0, 0, h / 2) * Cylinder(rp, h)
    post = chamfer(post.edges().group_by(Axis.Z)[-1], 1.0)
    body = Pos(0, 0, -BASE_T / 2) * Cylinder(r_base, BASE_T) + post
    body -= Pos(0, 0, (h - BASE_T) / 2) * Cylinder(BORE / 2, h + BASE_T + 1)          # wires
    body -= Pos(0, 0, -BASE_T + 1.5) * Box(22, 12, 3.0)                               # USB-C board, from below
    body -= Pos(r_base / 2 + 5, 0, -BASE_T + 1.5) * Box(r_base, 9.5, 3.0)              # its socket, to the edge
    floor = rp - (SHOE_T - SHOE_OUT) - SHOE_GAP                                       # bottom of the shoe's slot
    half = BAR_HALF_ARC + 4.0                                                         # the shoe is longer than its bars
    body -= Pos(0, 0, zc) * sector(floor, rp + 1, half + math.degrees(SHOE_GAP / rp), SHOE_H + 2 * SHOE_GAP)
    body -= Pos((floor + BORE / 2) / 2, 0, zc) * Box(floor - BORE / 2 + 1, 2.4, SHOE_H - 1.0)   # leads, slot to bore
    for side in (-1, 1):
        body -= (Rot(0, 0, side * (half - 8.0)) * Pos(floor - SPRING[1] / 2 + 0.01, 0, zc)
                 * radial * Cylinder(SPRING[0] / 2, SPRING[1]))
        # where the button must stop: one groove for each way round the ring can go on
        body -= (Rot(0, 0, side * rep["button_from_bars_deg"])
                 * Pos(p.outer_diameter / 2 + 1.0 + 2.0, 0, 0) * Box(4.0, 0.8, 1.2))

    face = floor + SHOE_GAP + SHOE_T                                                  # = rp + SHOE_OUT
    shoe = Pos(0, 0, zc) * sector(face - SHOE_T, face, half, SHOE_H)
    deep = SHOE_T - SHOE_FACE + 1.0                                                   # through the curved back
    shoe -= Pos(face - SHOE_FACE - deep / 2, 0, zc) * Box(deep, MAGNET[0] + 0.1, MAGNET[1] + 0.1)   # magnet, in from the back
    for z in rep["bar_z"]:
        shoe -= Pos(0, 0, z) * Torus(face + BAR_PROUD - BAR_D / 2, BAR_D / 2 + 0.03)   # groove for the bar
        for side in (-1, 1):                                                          # its two ends turn in and go through
            shoe -= (Rot(0, 0, side * BAR_HALF_ARC) * Pos(face - SHOE_T / 2, 0, z)
                     * radial * Cylinder(BAR_D / 2 + 0.08, SHOE_T + 1))
    return body, shoe


if __name__ == "__main__":
    from build123d import export_stl
    out, parts = S.ROOT / "mechanical" / "out", S.load_parts()
    for size in S.SIZES:
        rep = dock_report(ENVELOPES["B"].for_size(size), parts)
        body, shoe = build("B", size)
        export_stl(body, str(out / f"print-dock-US{size}.stl"))
        export_stl(shoe, str(out / f"print-dock-shoe-US{size}.stl"))
        print(f"US {size}: post {rep['post_diameter']} x {rep['post_height']}, button {rep['button_from_bars_deg']} deg from the bars, "
              f"turn tolerance +/-{rep['turn_tolerance_deg']} deg, magnet pull about {rep['magnet']['pull_N']} N"
              f"  {'ok' if rep['ok'] else 'FAIL ' + '; '.join(rep['problems'])}")
    print("print-dock-US*.stl and print-dock-shoe-US*.stl written")
