"""SVG drawings for the design document: plan view and one cross-section per island."""
import math

from . import stack as S
from .checks import _boxes, arc_report, best_cell, cell_report, contacts_report, island_report
from .params import ENVELOPES
from .profile import outline, shell_outline

INK, TI, RESIN, BOARD, PART, CELL = "#222", "#b9b2a6", "#f1ead9", "#3d7a4f", "#33475b", "#c2603c"
GOLD, STEEL = "#d9a520", "#7d8790"


def _svg(body, box, width):
    x, y, w, h = box
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x:.2f} {y:.2f} {w:.2f} {h:.2f}" '
            f'width="{width}" font-family="sans-serif">\n<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" '
            f'height="{h:.2f}" fill="#fff"/>\n{body}</svg>\n')


def _poly(pts, fill, stroke=INK, sw=0.03):
    d = " ".join(f"{a:.3f},{b:.3f}" for a, b in pts)
    return f'<polygon points="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>\n'


def plan(key: str) -> str:
    """View along the finger. 90 deg (back of the finger) is up."""
    p, parts = ENVELOPES[key], S.load_parts()
    ck = best_cell(p, parts) or S.DEFAULT_CELL[key]
    ro, ri = p.mean_radius + p.half_wall + p.crown, p.mean_radius - p.half_wall - p.crown
    xy = lambda r, deg: (r * math.cos(math.radians(deg)), -r * math.sin(math.radians(deg)))
    body = (f'<circle r="{ro:.3f}" fill="{TI}" stroke="{INK}" stroke-width="0.04"/>\n'
            f'<circle r="{ro - p.t_ti:.3f}" fill="{RESIN}" stroke="{INK}" stroke-width="0.02"/>\n'
            f'<circle r="{ri:.3f}" fill="#fff" stroke="{INK}" stroke-width="0.04"/>\n')
    cell = cell_report(p, parts, ck)
    t = parts["cells"][ck]["size"][2]
    layout = arc_report(p, parts, ck)
    a0 = layout["cell_centre_deg"] - cell["arc_deg"] / 2
    arc = [a0 + cell["arc_deg"] * i / 40 for i in range(41)]
    body += _poly([xy(cell["radius"] + t / 2, a) for a in arc]
                  + [xy(cell["radius"] - t / 2, a) for a in reversed(arc)], CELL)
    for isl, where in zip(S.ISLANDS, layout["placed"]):
        rp = island_report(p, parts, isl)["plane_radius"] or p.mean_radius
        c, s = math.cos(math.radians(where["centre_deg"])), math.sin(math.radians(where["centre_deg"]))
        for x0, x1, _, _, z0, z1, is_part in _boxes(parts, isl):
            corners = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
            body += _poly([((rp + z) * c - x * s, -((rp + z) * s + x * c)) for x, z in corners],
                          PART if is_part else BOARD, sw=0.015)
        lx, ly = xy(ro + 1.6, where["centre_deg"])
        body += (f'<text x="{lx:.2f}" y="{ly:.2f}" font-size="0.9" text-anchor="middle" '
                 f'dominant-baseline="middle">{isl.name}</text>\n')
    lx, ly = xy(ro + 1.6, layout["cell_centre_deg"])
    body += f'<text x="{lx:.2f}" y="{ly:.2f}" font-size="0.9" text-anchor="middle">cell</text>\n'
    m = ro + 4.2
    return _svg(body, (-m, -m, 2 * m, 2 * m), 640)


def section(key: str, island_name: str) -> str:
    """Cross-section through the middle of one island: band width across, outside up."""
    p, parts = ENVELOPES[key], S.load_parts()
    isl = next(i for i in S.ISLANDS if i.name == island_name)
    rp = (island_report(p, parts, isl)["plane_radius"] or p.mean_radius) - p.mean_radius
    flip = lambda pts: [(y, -rho) for rho, y in pts]
    body = _poly(flip(outline(p)), TI)
    body = _poly(flip(outline(p)), RESIN) + _poly(flip(shell_outline(p)), TI)
    for _, _, y0, y1, z0, z1, is_part in _boxes(parts, isl):
        body += _poly(flip([(rp + z0, y0), (rp + z1, y0), (rp + z1, y1), (rp + z0, y1)]),
                      PART if is_part else BOARD, sw=0.015)
    if island_name == "contacts":           # the slugs down to the inner surface, the keeper above the parts
        con, t = contacts_report(p, parts), isl.thickness / 2
        for s in con["slugs"]:
            lo, hi, y0, y1 = rp - t - s["height"], rp - t, s["y"] - s["diameter"] / 2, s["y"] + s["diameter"] / 2
            body += _poly(flip([(lo, y0), (hi, y0), (hi, y1), (lo, y1)]), GOLD, sw=0.015)
        _, _, y0, y1, z0, z1 = con["keeper"]["box"]
        body += _poly(flip([(rp + z0, y0), (rp + z1, y0), (rp + z1, y1), (rp + z0, y1)]), STEEL, sw=0.015)
    body += (f'<text x="0" y="{p.half_wall + p.crown + 0.7:.2f}" font-size="0.45" '
             f'text-anchor="middle">{p.name}: {isl.name} island (finger side down)</text>\n')
    m = p.half_width + 0.6
    h = p.half_wall + p.crown + 1.0
    return _svg(body, (-m, -h, 2 * m, 2 * h), 640)


if __name__ == "__main__":
    out = S.ROOT / "mechanical" / "out"
    for key in ENVELOPES:
        (out / f"plan-{key}.svg").write_text(plan(key))
        for isl in S.ISLANDS:
            (out / f"section-{key}-{isl.name}.svg").write_text(section(key, isl.name))
    print("drawings written to", out)
