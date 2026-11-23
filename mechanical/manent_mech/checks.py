"""Fit checks: does everything in stack.py go inside the envelope in params.py?"""
import json
import math
from itertools import combinations

from . import stack as S
from .params import ENVELOPES, RingParams
from .profile import cavity_height, in_cavity, in_titanium, sdf



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
        if not pl.fitted:                   # a land pattern with nothing on it takes no height
            continue
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


_ISLAND_CACHE: dict = {}


def island_report(p: RingParams, parts, isl) -> dict:
    key = (p, isl)
    if key not in _ISLAND_CACHE:
        _ISLAND_CACHE[key] = _island_report(p, parts, isl)
    return _ISLAND_CACHE[key]


def _island_report(p: RingParams, parts, isl) -> dict:
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
        max((_size(parts, pl)[2] + S.SOLDER for pl in isl.parts if pl.face == f and pl.fitted), default=0.0)
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


FLEX_SLACK = 0.15       # flex beyond the straight distance between two board ends
MIN_BEND_RATIO = 10     # fold radius over flex thickness, for a flex bent once


def chain(p: RingParams, parts) -> dict:
    """Lay the islands one after the other round the ring. Each is a flat board at its own
    depth in the wall; the flex between two of them is FLEX_SLACK longer than the straight
    distance between their ends. Angles are in degrees from the tab end of the cell."""
    def ends(isl, deg):
        r = island_report(p, parts, isl)["plane_radius"] or p.mean_radius
        a = math.radians(deg)
        c, t = (r * math.cos(a), r * math.sin(a)), (-math.sin(a), math.cos(a))
        h = isl.length / 2
        return (c[0] - t[0] * h, c[1] - t[1] * h), (c[0] + t[0] * h, c[1] + t[1] * h), r

    mm = lambda length: math.degrees(length / p.mean_radius)
    centres, bends, prev, deg = {}, [], None, mm(S.CELL_TABS + S.BENDS[0])
    for i, isl in enumerate(S.ISLANDS):
        half = math.degrees(math.atan2(isl.length / 2, island_report(p, parts, isl)["plane_radius"] or p.mean_radius))
        if prev is None:
            centre = deg + half
        else:
            want = S.BENDS[i] - FLEX_SLACK
            lo = prev[1] + prev[3] + half             # board ends level with each other
            hi = lo + 40.0
            for _ in range(50):
                m = (lo + hi) / 2
                if math.dist(prev[0], ends(isl, m)[0]) < want:
                    lo = m
                else:
                    hi = m
            centre = hi
            start, _, r = ends(isl, centre)
            turn = math.radians(centre - prev[1])
            radius = S.BENDS[i] / turn if turn > 0 else float("inf")
            reachable = math.dist(prev[0], start) <= want + 1e-6
            bends.append({"between": f"{S.ISLANDS[i - 1].name} - {isl.name}", "flex": S.BENDS[i],
                          "depth_step": round(abs(r - prev[2]), 2), "fold_radius": round(radius, 2),
                          "radius_over_thickness": round(radius / S.FLEX_T),
                          "ok": reachable and centre - half > prev[1] + prev[3] and radius / S.FLEX_T >= MIN_BEND_RATIO})
        centres[isl.name] = centre
        prev = (ends(isl, centre)[1], centre, ends(isl, centre)[2], half)
    total = prev[1] + prev[3] + mm(S.BENDS[-1])
    return {"centres": centres, "bends": bends, "total_deg": total}


def arc_report(p: RingParams, parts, cell_key: str) -> dict:
    """Place the chain of islands with the button at BUTTON_DEG; whatever arc is left over
    lies between the last island and the far end of the cell."""
    cell = cell_report(p, parts, cell_key)
    ch = chain(p, parts)
    start = S.BUTTON_DEG - ch["centres"]["button"]      # angle of the tab end of the cell
    slack_mm = math.radians(360.0 - cell["arc_deg"] - ch["total_deg"]) * p.mean_radius - S.CLOSING_GAP
    placed, problems = [], []
    for isl in S.ISLANDS:
        centre = start + ch["centres"][isl.name]
        placed.append({"island": isl.name, "centre_deg": round(centre, 1)})
        if isl.target_deg and not isl.target_deg[0] <= centre <= isl.target_deg[1]:
            problems.append(f"{isl.name} at {centre:.0f} deg, wanted {isl.target_deg}")
    return {"electronics_mm": round(math.radians(ch["total_deg"]) * p.mean_radius, 2), "cell_arc_deg": cell["arc_deg"],
            "cell_centre_deg": round(start - cell["arc_deg"] / 2, 1),
            "slack_mm": round(slack_mm, 2), "placed": placed,
            "ok": slack_mm >= 0 and not problems, "problems": problems}


def max_cell_length(p: RingParams, parts, cell_key: str) -> float:
    """Longest cell of this cross-section that leaves room for the electronics."""
    cell = cell_report(p, parts, cell_key)
    free = math.radians(360.0 - chain(p, parts)["total_deg"]) * p.mean_radius - S.CLOSING_GAP
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
            if in_titanium(p, rho, y):
                ti += ring
            else:
                fill += ring
    return {"titanium_g": round(ti * 4.43e-3, 2), "filling_g_estimate": round(fill * 1.6e-3, 2),
            "total_g_estimate": round(ti * 4.43e-3 + fill * 1.6e-3, 2)}


def board_length() -> float:
    """Length of the flat board, tabs to the end of the last island."""
    assert len(S.BENDS) == len(S.ISLANDS) + 1
    return S.CELL_TABS + sum(i.length for i in S.ISLANDS) + sum(S.BENDS[:-1])


def bend_report(p: RingParams, parts) -> list[dict]:
    return chain(p, parts)["bends"]


def envelope_report(key: str, us_size: float | None = None, cell_key: str | None = None) -> dict:
    parts = S.load_parts()
    p = ENVELOPES[key] if us_size is None else ENVELOPES[key].for_size(us_size)
    cell_key = cell_key or best_cell(p, parts) or S.DEFAULT_CELL[key]
    islands = [island_report(p, parts, i) for i in S.ISLANDS]
    cell = cell_report(p, parts, cell_key)
    arc = arc_report(p, parts, cell_key)
    bends = bend_report(p, parts)
    return {
        "envelope": p.name, "us_size": round(p.us_size, 2),
        "band_width": p.band_width, "wall_edge": round(p.wall_edge, 2),
        "wall_centre": round(p.wall_centre, 2),
        "inner_diameter": round(p.inner_diameter_min, 2), "outer_diameter": round(p.outer_diameter, 2),
        "cavity_height": {str(w): round(cavity_height(p, w), 2) for w in (4.0, 5.0, 5.6, 6.0, 6.5)},
        "islands": islands, "cell": cell, "arc": arc, "bends": bends, "mass": mass_report(p),
        "ok": all(i["ok"] for i in islands) and cell["ok"] and arc["ok"] and all(b["ok"] for b in bends),
    }


def sensitivity(key: str = "B") -> list[dict]:
    """How the tightest island and the cell respond to the two least certain numbers."""
    from dataclasses import replace
    parts, p = S.load_parts(), ENVELOPES[key]
    rows = []
    for t in (0.40, 0.45, 0.50, 0.55, 0.60):
        worst = min(island_report(p, parts, replace(i, thickness=t))["clearance"] for i in S.ISLANDS)
        rows.append({"what": f"island thickness {t:.2f}", "margin": round(worst - p.gap, 3), "ok": worst >= p.gap})
    nominal = S.SWELL
    try:
        for swell in (0.0, 0.05, 0.08, 0.10):
            S.SWELL = swell
            for key, cell in parts["cells"].items():
                c = cell_report(p, parts, key)["clearance"]
                rows.append({"what": f"{cell['mpn']} ({cell['size'][2]} x {cell['size'][1]}) swollen {swell:.0%}",
                             "margin": round(c - S.CELL_GAP, 3), "ok": c >= S.CELL_GAP})
    finally:
        S.SWELL = nominal
    return rows


def best_cell(p: RingParams, parts) -> str | None:
    """Largest catalogue cell that fits both the cross-section and the arc."""
    fitting = [(c["capacity_mah"], k) for k, c in parts["cells"].items()
               if cell_report(p, parts, k)["ok"] and arc_report(p, parts, k)["slack_mm"] >= 0]
    return max(fitting)[1] if fitting else None


def islands_ok(p: RingParams, parts) -> bool:
    return all(island_report(p, parts, i)["ok"] for i in S.ISLANDS)


def size_sweep(key: str, sizes=S.SIZES) -> list[dict]:
    parts = S.load_parts()
    rows = []
    for size in sizes:
        p = ENVELOPES[key].for_size(size)
        ck = best_cell(p, parts)
        best = (parts["cells"][ck]["capacity_mah"], ck) if ck else None
        worst = min(island_report(p, parts, i)["clearance"] for i in S.ISLANDS)
        rows.append({"us_size": size, "inner_diameter": round(p.inner_diameter_min, 2),
                     "islands_fit": worst >= p.gap, "tightest_island": round(worst, 3),
                     "max_cell_length": round(max_cell_length(p, parts, S.DEFAULT_CELL[key]), 1),
                     "best_cell": best[1] if best else None,
                     "capacity_mah": best[0] if best else None})
    return rows


def full_report() -> dict:
    return {"envelopes": {k: envelope_report(k) for k in ENVELOPES},
            "size_sweep": {k: size_sweep(k) for k in ENVELOPES}, "sensitivity": sensitivity()}


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
        for b in e["bends"]:
            print(f"  bend {b['between']:<20} flex {b['flex']:.1f}  depth step {b['depth_step']:.2f}"
                  f"  fold r/t {b['radius_over_thickness']:.0f}  {'ok' if b['ok'] else 'FAIL'}")
        print("  mass:", e["mass"])
    for k, rows in rep["size_sweep"].items():
        print(f"\n== sizes, envelope {k}")
        for r in rows:
            print(f"  US {r['us_size']:>2}  inner {r['inner_diameter']:.2f}  max cell {r['max_cell_length']:.1f} mm"
                  f"  best {r['best_cell']} ({r['capacity_mah']} mAh)"
                  f"  islands {'fit' if r['islands_fit'] else 'DO NOT FIT'} ({r['tightest_island']:+.3f})")
    for r in rep["sensitivity"]:
        print(f"  {r['what']}: margin {r['margin']:+.3f}  {'ok' if r['ok'] else 'FAIL'}")
