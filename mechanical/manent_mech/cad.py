"""Solid model of the ring for STEP export and a visual check. Run as a module."""
import math

from build123d import Axis, Box, Compound, Cylinder, Plane, Polygon, Pos, Rot, export_step, export_stl, revolve

from . import stack as S
from .checks import _boxes, arc_report, best_cell, cell_report, contacts_report, island_report
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


def contact_bodies(p, parts, cell_key, dimple=0.0, pocket=0.0):
    """The contact slugs and the steel keeper, in place. With `dimple`, each slug is only
    that deep from the inner surface; with `pocket`, the keeper reaches that much further out."""
    con = contacts_report(p, parts)
    deg = next(w["centre_deg"] for w in arc_report(p, parts, cell_key)["placed"] if w["island"] == "contacts")
    r, t = con["plane_radius"], S.RIGID_T / 2
    slugs = []
    for s in con["slugs"]:
        h = dimple + 0.2 if dimple else s["height"]            # a dimple starts 0.2 inside the bore
        mid = r - t - s["height"] + (dimple - 0.2) / 2 if dimple else r - t - h / 2
        slug = Rot(0, 0, deg) * Pos(mid, s["x"], s["y"]) * Rot(0, 90, 0) * Cylinder(s["diameter"] / 2, h)
        slug.label = f"contact {s['pad']}"
        slugs.append(slug)
    x0, x1, y0, y1, z0, z1 = con["keeper"]["box"]
    z1 += pocket
    keeper = Rot(0, 0, deg) * Pos(r + (z0 + z1) / 2, (x0 + x1) / 2, (y0 + y1) / 2) * Box(z1 - z0, x1 - x0, y1 - y0)
    keeper.label = "steel keeper"
    return slugs, keeper


def printable(key: str, us_size: float | None = None):
    """Two bodies to 3D print for a first look: the outer shell with its three openings, and
    the whole ring as one solid block to try on a finger. The block has a dimple on each
    contact and a pocket, open to the outside, that puts a steel plate where the keeper will
    be: with a printed dock (dock.py) it shows whether the magnets find the pins."""
    p = ENVELOPES[key] if us_size is None else ENVELOPES[key].for_size(us_size)
    parts = S.load_parts()
    ck = best_cell(p, parts) or S.DEFAULT_CELL[key]
    shell = _revolved(shell_outline(p), p.mean_radius)
    r_out = p.mean_radius + p.half_wall + p.crown
    for angle, y, kind in openings(p, parts, ck):
        if kind == "button":                # a slot for the cap, long side across the band
            cut = Box(2.0, 1.8, 2.8)
        else:
            cut = Rot(0, 90, 0) * Cylinder(0.4 if kind == "microphone" else 0.3, 2.0)
        shell -= Rot(0, 0, angle) * Pos(r_out - 0.5, 0, y) * cut
    block = _revolved(outline(p, 160), p.mean_radius)
    dimples, pocket = contact_bodies(p, parts, ck, dimple=0.25, pocket=3.0)
    for cut in (*dimples, pocket):
        block -= cut
    return shell, block


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

    slugs, keeper = contact_bodies(p, parts, ck)
    solids += [*slugs, keeper]

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
    from .dock import build as build_dock
    for size in S.SIZES:
        body, shoe = build_dock("B", size)
        export_stl(body, str(out / f"print-dock-US{size}.stl"))
        export_stl(shoe, str(out / f"print-dock-shoe-US{size}.stl"))
    print("print-shell-*.stl and print-block-*.stl written for the reference size and each size offered;"
          " print-dock-*.stl for each size")
