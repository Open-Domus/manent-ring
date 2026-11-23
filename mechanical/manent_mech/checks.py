"""Fit checks: does everything in stack.py go inside the envelope in params.py?"""
import json
import math
from itertools import combinations

from . import stack as S
from .params import ENVELOPES, RingParams
from .profile import cavity_height, in_cavity, sdf



EDGE = S.EDGE_MARGIN - 1e-6        # the packer places parts exactly at these limits
SPACING = S.PART_SPACING - 1e-6


def _size(parts, pl):
    l, w, h = parts["parts"][pl.part]["size"]
    return (w, l, h) if pl.turned else (l, w, h)


def _boxes(parts, isl):
    """Boxes of an island in local coordinates: (x0, x1, y0, y1, z0, z1, is_part)."""
    t = isl.thickness / 2
    out = [(-isl.length / 2, isl.length / 2, -S.FLEX_WIDTH / 2, S.FLEX_WIDTH / 2, -t, t, False)]
    for pl in isl.parts:
        l, w, h = _size(parts, pl)
        z = (t, t + S.SOLDER + h) if pl.face == "out" else (-t - S.SOLDER - h, -t)
        out.append((pl.x - l / 2, pl.x + l / 2, pl.y - w / 2, pl.y + w / 2, z[0], z[1], True))
    return out


def _fits(p, boxes, r_plane, gap):
    for x0, x1, y0, y1, z0, z1, is_part in boxes:
        g = gap if is_part else min(gap, 0.03)     # the bare board may touch the wall
        for i in range(5):
            x = x0 + (x1 - x0) * i / 4
            for y in (y0, (y0 + y1) / 2, y1):
                for z in (z0, z1):
                    rho = math.hypot(x, r_plane + z) - p.mean_radius
                    if not in_cavity(p, rho, y, g):
                        return False
    return True


def _range(p, boxes, gap):
    """Lowest and highest plane radius at which the boxes fit, or None."""
    ok = [r for r in (p.mean_radius - 1.6 + 0.005 * i for i in range(640))
          if _fits(p, boxes, r, gap)]
    return (ok[0], ok[-1]) if ok else None


def _clearance(p, boxes):
    """Largest resin thickness that can surround the boxes (negative: they do not fit)."""
    lo, hi = -0.6, 1.0
    for _ in range(12):
        m = (lo + hi) / 2
        if _range(p, boxes, m):
            lo = m
        else:
            hi = m
    return lo


def island_report(p: RingParams, parts, isl) -> dict:
    boxes = _boxes(parts, isl)
    c = _clearance(p, boxes)
    rng = _range(p, boxes, min(c, p.gap))
    problems = []
    rects = []
    for pl in isl.parts:
        l, w, _ = _size(parts, pl)
        r = (pl.x - l / 2, pl.x + l / 2, pl.y - w / 2, pl.y + w / 2, pl.face, pl.part)
        if (r[0] < -isl.length / 2 + EDGE or r[1] > isl.length / 2 - EDGE
                or r[2] < -S.FLEX_WIDTH / 2 + EDGE or r[3] > S.FLEX_WIDTH / 2 - EDGE):
            problems.append(f"{pl.part} overhangs the island")
        rects.append(r)
    for a, b in combinations(rects, 2):
        if a[4] == b[4] and (a[0] < b[1] + SPACING and b[0] < a[1] + SPACING
                             and a[2] < b[3] + SPACING and b[2] < a[3] + SPACING):
            problems.append(f"{a[5]} and {b[5]} overlap")
    stack_h = isl.thickness + sum(
        max((_size(parts, pl)[2] + S.SOLDER for pl in isl.parts if pl.face == f), default=0.0)
        for f in ("in", "out"))
    return {"island": isl.name, "length": isl.length, "stack_height": round(stack_h, 3),
            "clearance": round(c, 3), "plane_radius": round({"mid": sum(rng) / 2, "out": rng[1], "in": rng[0]}[isl.seat], 3) if rng else None,
            "ok": c >= p.gap and not problems, "problems": problems}


def cell_report(p: RingParams, parts, key: str) -> dict:
    cell = parts["cells"][key]
    length, width, thick = cell["size"]
    t = thick * (1 + S.SWELL)

    def fits(r_mid, gap):
        return all(in_cavity(p, r_mid + dz - p.mean_radius, y, gap)
                   for dz in (-t / 2, t / 2) for y in (-width / 2, 0.0, width / 2))

    lo, hi = -0.6, 1.0
    for _ in range(14):
        m = (lo + hi) / 2
        if any(fits(p.mean_radius - 1.6 + 0.005 * i, m) for i in range(640)):
            lo = m
        else:
            hi = m
    ok_r = [r for r in (p.mean_radius - 1.6 + 0.005 * i for i in range(640)) if fits(r, min(lo, S.CELL_GAP))]
    r_mid = (ok_r[0] + ok_r[-1]) / 2 if ok_r else p.mean_radius
    return {"cell": key, "mpn": cell["mpn"], "capacity_mah": cell["capacity_mah"],
            "size": cell["size"], "status": cell["status"], "clearance": round(lo, 3),
            "radius": round(r_mid, 3), "arc_deg": round(math.degrees(length / r_mid), 1),
            "ok": lo >= S.CELL_GAP}


def arc_report(p: RingParams, parts, cell_key: str) -> dict:
    """Lay the islands along the arc after the cell tabs, with the button at BUTTON_DEG;
    whatever arc is left over sits between the last island and the far end of the cell."""
    cell = cell_report(p, parts, cell_key)
    r = p.mean_radius
    mm = lambda length: math.degrees(length / r)
    ang, centres = mm(S.CELL_TABS), {}
    for isl in S.ISLANDS:
        ang += mm(S.BEND)
        centres[isl.name] = ang + mm(isl.length) / 2
        ang += mm(isl.length)
    ang += mm(S.BEND)
    start = S.BUTTON_DEG - centres["button"]            # angle of the tab end of the cell
    slack_mm = math.radians(360.0 - cell["arc_deg"] - ang) * r - S.CLOSING_GAP
    placed, problems = [], []
    for isl in S.ISLANDS:
        centre = start + centres[isl.name]
        placed.append({"island": isl.name, "centre_deg": round(centre, 1)})
        if isl.target_deg and not isl.target_deg[0] <= centre <= isl.target_deg[1]:
            problems.append(f"{isl.name} at {centre:.0f} deg, wanted {isl.target_deg}")
    used = S.CELL_TABS + sum(i.length for i in S.ISLANDS) + S.BEND * (len(S.ISLANDS) + 1)
    return {"electronics_mm": round(used, 2), "cell_arc_deg": cell["arc_deg"],
            "cell_centre_deg": round(start - cell["arc_deg"] / 2, 1),
            "slack_mm": round(slack_mm, 2), "placed": placed,
            "ok": slack_mm >= 0 and not problems, "problems": problems}


def max_cell_length(p: RingParams, parts, cell_key: str) -> float:
    """Longest cell of this cross-section that leaves room for the electronics."""
    cell = cell_report(p, parts, cell_key)
    used = S.CELL_TABS + sum(i.length for i in S.ISLANDS) + S.BEND * (len(S.ISLANDS) + 1)
    free = 2 * math.pi * p.mean_radius - used - S.CLOSING_GAP
    return free * cell["radius"] / p.mean_radius


def mass_report(p: RingParams) -> dict:
    """Titanium and filling volumes by integrating the cross-section around the axis."""
    n, ti, fill = 240, 0.0, 0.0
    span_r = p.half_wall + p.crown
    dr, dy = 2 * span_r / n, 2 * p.half_width / n
    for i in range(n):
        rho = -span_r + (i + 0.5) * dr
        for j in range(n):
            y = -p.half_width + (j + 0.5) * dy
            d = sdf(p, rho, y)
            if d >= 0:
                continue
            ring = 2 * math.pi * (p.mean_radius + rho) * dr * dy
            if abs(y) > p.half_width - p.t_ti or (rho > 0 and d > -p.t_ti):
                ti += ring
            else:
                fill += ring
    return {"titanium_g": round(ti * 4.43e-3, 2), "filling_g_estimate": round(fill * 1.6e-3, 2),
            "total_g_estimate": round(ti * 4.43e-3 + fill * 1.6e-3, 2)}


def flex_report(p: RingParams) -> dict:
    ratio = (p.mean_radius - 1.0) / S.FLEX_T
    return {"bend_radius_over_thickness": round(ratio, 0), "minimum": 10, "ok": ratio >= 10}


def envelope_report(key: str, us_size: float | None = None, cell_key: str | None = None) -> dict:
    parts = S.load_parts()
    p = ENVELOPES[key] if us_size is None else ENVELOPES[key].for_size(us_size)
    cell_key = cell_key or best_cell(p, parts) or S.DEFAULT_CELL[key]
    islands = [island_report(p, parts, i) for i in S.ISLANDS]
    cell = cell_report(p, parts, cell_key)
    arc = arc_report(p, parts, cell_key)
    return {
        "envelope": p.name, "us_size": round(p.us_size, 2),
        "band_width": p.band_width, "wall_edge": round(p.wall_edge, 2),
        "wall_centre": round(p.wall_centre, 2),
        "inner_diameter": round(p.inner_diameter_min, 2), "outer_diameter": round(p.outer_diameter, 2),
        "cavity_height": {str(w): round(cavity_height(p, w), 2) for w in (4.0, 5.0, 5.6, 6.0, 6.5)},
        "islands": islands, "cell": cell, "arc": arc, "flex": flex_report(p), "mass": mass_report(p),
        "ok": all(i["ok"] for i in islands) and cell["ok"] and arc["ok"],
    }


def best_cell(p: RingParams, parts) -> str | None:
    """Largest catalogue cell that fits both the cross-section and the arc."""
    fitting = [(c["capacity_mah"], k) for k, c in parts["cells"].items()
               if cell_report(p, parts, k)["ok"] and arc_report(p, parts, k)["slack_mm"] >= 0]
    return max(fitting)[1] if fitting else None


def size_sweep(key: str, sizes=range(6, 14)) -> list[dict]:
    parts = S.load_parts()
    rows = []
    for size in sizes:
        p = ENVELOPES[key].for_size(size)
        ck = best_cell(p, parts)
        best = (parts["cells"][ck]["capacity_mah"], ck) if ck else None
        rows.append({"us_size": size, "inner_diameter": round(p.inner_diameter_min, 2),
                     "max_cell_length": round(max_cell_length(p, parts, S.DEFAULT_CELL[key]), 1),
                     "best_cell": best[1] if best else None,
                     "capacity_mah": best[0] if best else None})
    return rows


def full_report() -> dict:
    return {"envelopes": {k: envelope_report(k) for k in ENVELOPES},
            "size_sweep": {k: size_sweep(k) for k in ENVELOPES}}


if __name__ == "__main__":
    rep = full_report()
    out = S.ROOT / "mechanical" / "out" / "fit-report.json"
    out.write_text(json.dumps(rep, indent=2) + "\n")
    for k, e in rep["envelopes"].items():
        print(f"\n== {e['envelope']}  US {e['us_size']}  {e['band_width']} x {e['wall_edge']}-{e['wall_centre']} mm"
              f"  -> {'FITS' if e['ok'] else 'DOES NOT FIT'}")
        print("  cavity height by width:", e["cavity_height"])
        for i in e["islands"]:
            print(f"  {i['island']:<11} stack {i['stack_height']:.2f}  clearance {i['clearance']:+.2f}"
                  f"  {'ok' if i['ok'] else 'FAIL'} {'; '.join(i['problems'])}")
        c = e["cell"]
        print(f"  cell {c['mpn']} {c['capacity_mah']} mAh  clearance {c['clearance']:+.2f}  arc {c['arc_deg']} deg"
              f"  {'ok' if c['ok'] else 'FAIL'}")
        a = e["arc"]
        print(f"  arc: electronics {a['electronics_mm']} mm, slack {a['slack_mm']:+.1f} mm  "
              f"{'ok' if a['ok'] else 'FAIL'} {'; '.join(a['problems'])}")
        print("   ", ", ".join(f"{x['island']}@{x['centre_deg']:.0f}" for x in a["placed"]))
        print("  mass:", e["mass"])
    for k, rows in rep["size_sweep"].items():
        print(f"\n== sizes, envelope {k}")
        for r in rows:
            print(f"  US {r['us_size']:>2}  inner {r['inner_diameter']:.2f}  max cell {r['max_cell_length']:.1f} mm"
                  f"  best {r['best_cell']} ({r['capacity_mah']} mAh)")
