"""Solid model of the ring for STEP export and a visual check. Run as a module."""
import math

from build123d import Axis, Box, Compound, Cylinder, Plane, Polygon, Pos, Rot, export_step, export_stl, revolve

from . import stack as S
from .checks import _boxes, arc_report, best_cell, cell_report, island_report
from .params import ENVELOPES
from .profile import outline, shell_outline


def _revolved(points, r0, degrees=360.0):
    face = Plane.XZ * Polygon(*[(r0 + rho, y) for rho, y in points], align=None)
    return revolve(face, Axis.Z, degrees)


def openings(p, parts, cell_key):
    """Where the shell is pierced, from the layout: (angle in degrees, axial position, kind)."""
    where = {w["island"]: w["centre_deg"] for w in arc_report(p, parts, cell_key)["placed"]}
    out = []
    for isl in S.ISLANDS:
        r = island_report(p, parts, isl)["plane_radius"] or p.mean_radius
        for pl in isl.parts:
            x, y, kind = pl.x, pl.y, {"mic": "microphone", "led": "light", "button": "button"}.get(pl.part)
            if pl.part == "mic":            # the port is off the body centre, along its length
                x, y = (x, y - S.PORT_OFFSET) if pl.turned else (x - S.PORT_OFFSET, y)
            if kind:
                out.append((where[isl.name] + math.degrees(x / r), y, kind))
    return out


def printable(key: str, us_size: float | None = None):
    """Two bodies to 3D print for a first look: the outer shell with its three openings, and
    the whole ring as one solid block to try on a finger."""
    p = ENVELOPES[key] if us_size is None else ENVELOPES[key].for_size(us_size)
    parts = S.load_parts()
    shell = _revolved(shell_outline(p), p.mean_radius)
    r_out = p.mean_radius + p.half_wall + p.crown
    for angle, y, kind in openings(p, parts, best_cell(p, parts) or S.DEFAULT_CELL[key]):
        if kind == "button":                # a slot for the cap, long side across the band
            cut = Box(2.0, 1.8, 2.8)
        else:
            cut = Rot(0, 90, 0) * Cylinder(0.4 if kind == "microphone" else 0.3, 2.0)
        shell -= Rot(0, 0, angle) * Pos(r_out - 0.5, 0, y) * cut
    return shell, _revolved(outline(p, 160), p.mean_radius)


def build(key: str) -> Compound:
    p = ENVELOPES[key]
    parts = S.load_parts()
    shell = _revolved(shell_outline(p), p.mean_radius)
    shell.label = "titanium shell"

    solids = [shell]
    ck = best_cell(p, parts) or S.DEFAULT_CELL[key]
    arc = arc_report(p, parts, ck)
    for isl, where in zip(S.ISLANDS, arc["placed"]):
        r_plane = island_report(p, parts, isl)["plane_radius"] or p.mean_radius
        fitted = [pl for pl in isl.parts if pl.fitted]
        for n, (x0, x1, y0, y1, z0, z1, is_part) in enumerate(_boxes(parts, isl)):
            box = (Rot(0, 0, where["centre_deg"])
                   * Pos(r_plane + (z0 + z1) / 2, (x0 + x1) / 2, (y0 + y1) / 2)
                   * Box(z1 - z0, x1 - x0, y1 - y0))
            box.label = f"{isl.name}/{fitted[n - 1].part if is_part else 'board'}"
            solids.append(box)

    cell = cell_report(p, parts, ck)
    length, width, thick = parts["cells"][ck]["size"]
    rect = [(-thick / 2, -width / 2), (thick / 2, -width / 2), (thick / 2, width / 2), (-thick / 2, width / 2)]
    body = Rot(0, 0, arc["cell_centre_deg"] - cell["arc_deg"] / 2) * _revolved(rect, cell["radius"], cell["arc_deg"])
    body.label = f"cell {ck}"
    solids.append(body)
    return Compound(label=f"manent-ring-{key}", children=solids)


if __name__ == "__main__":
    out = S.ROOT / "mechanical" / "out"
    for key in ENVELOPES:
        model = build(key)
        export_step(model, str(out / f"ring-{key}.step"))
        print(f"ring-{key}.step: {len(model.children)} bodies, "
              f"bounding box {tuple(round(v, 2) for v in model.bounding_box().size)}")
    # For 3D printing, in the adopted envelope: reference size and whole US sizes.
    for size in (None, *S.SIZES):
        shell, block = printable("B", size)
        tag = "reference" if size is None else f"US{size}"
        export_stl(shell, str(out / f"print-shell-{tag}.stl"))
        export_stl(block, str(out / f"print-block-{tag}.stl"))
    print("print-shell-*.stl and print-block-*.stl written for the reference size and each size offered")
