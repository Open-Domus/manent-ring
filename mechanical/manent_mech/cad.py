"""Solid model of the ring for STEP export and a visual check. Run as a module."""
import math

from build123d import Axis, Box, Compound, Plane, Polygon, Pos, Rot, export_step, export_stl, revolve

from . import stack as S
from .checks import _boxes, arc_report, best_cell, cell_report, island_report
from .params import ENVELOPES
from .profile import cavity_limits, half_wall_at, outline


def _revolved(points, r0, degrees=360.0):
    face = Plane.XZ * Polygon(*[(r0 + rho, y) for rho, y in points], align=None)
    return revolve(face, Axis.Z, degrees)


def printable(key: str, us_size: float | None = None):
    """Two bodies to 3D print for a first look: the outer shell as designed, and the whole
    ring as one solid block to try on a finger."""
    p = ENVELOPES[key] if us_size is None else ENVELOPES[key].for_size(us_size)
    w = p.half_width - p.t_ti - 0.01
    ys = [-w + 2 * w * i / 79 for i in range(80)]
    fill_pts = ([((cavity_limits(p, y) or (0.0, 0.0))[1], y) for y in ys]
                + [(-half_wall_at(p, y), y) for y in reversed(ys)])
    band = _revolved(outline(p, 160), p.mean_radius)
    return band - _revolved(fill_pts, p.mean_radius), band


def build(key: str) -> Compound:
    p = ENVELOPES[key]
    parts = S.load_parts()
    w = p.half_width - p.t_ti - 0.01
    ys = [-w + 2 * w * i / 79 for i in range(80)]
    fill_pts = ([((cavity_limits(p, y) or (0.0, 0.0))[1], y) for y in ys]
                + [(-half_wall_at(p, y), y) for y in reversed(ys)])
    band = _revolved(outline(p, 160), p.mean_radius)
    fill = _revolved(fill_pts, p.mean_radius)
    shell = band - fill
    shell.label = "titanium shell"

    solids = [shell]
    ck = best_cell(p, parts) or S.DEFAULT_CELL[key]
    arc = arc_report(p, parts, ck)
    for isl, where in zip(S.ISLANDS, arc["placed"]):
        r_plane = island_report(p, parts, isl)["plane_radius"] or p.mean_radius
        for n, (x0, x1, y0, y1, z0, z1, is_part) in enumerate(_boxes(parts, isl)):
            box = (Rot(0, 0, where["centre_deg"])
                   * Pos(r_plane + (z0 + z1) / 2, (x0 + x1) / 2, (y0 + y1) / 2)
                   * Box(z1 - z0, x1 - x0, y1 - y0))
            box.label = f"{isl.name}/{isl.parts[n - 1].part if is_part else 'board'}"
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
    for size in (None, 6, 7, 8, 9, 10, 11, 12, 13):
        shell, block = printable("B", size)
        tag = "reference" if size is None else f"US{size}"
        export_stl(shell, str(out / f"print-shell-{tag}.stl"))
        export_stl(block, str(out / f"print-block-{tag}.stl"))
    print("print-shell-*.stl and print-block-*.stl written for the reference size and US 6-13")
