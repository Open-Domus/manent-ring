"""Cross-section geometry: the band outline and the cavity left for the electronics.

Coordinates: rho = radius - mean_radius (positive outwards), y = axial position.
"""
import math

from .params import RingParams


def half_wall_at(p: RingParams, y: float) -> float:
    k = max(-1.0, min(1.0, y / p.half_width))
    return p.half_wall + p.crown * (1 - k * k)


def sdf(p: RingParams, rho: float, y: float) -> float:
    """Signed distance to the band outline (negative inside). Same formula as ring.js."""
    hx = half_wall_at(p, y)
    dx = abs(rho) - (hx - p.corner_r)
    dy = abs(y) - (p.half_width - p.corner_r)
    outside = math.hypot(max(dx, 0.0), max(dy, 0.0))
    return outside + min(max(dx, dy), 0.0) - p.corner_r


def in_cavity(p: RingParams, rho: float, y: float, gap: float | None = None) -> bool:
    """True if the point may hold a part: behind the titanium (outer face and side
    walls), above the resin skin (inner face), with `gap` of resin all around."""
    g = p.gap if gap is None else gap
    if abs(y) > p.half_width - p.t_ti - g:
        return False
    if rho < -half_wall_at(p, y) + p.t_skin + g:
        return False
    if rho > 0 and sdf(p, rho, y) > -(p.t_ti + g):
        return False
    return True


def cavity_limits(p: RingParams, y: float, gap: float = 0.0) -> tuple[float, float] | None:
    """Lowest and highest rho available at axial position y, or None if there is none."""
    if abs(y) > p.half_width - p.t_ti - gap:
        return None
    lo = -half_wall_at(p, y) + p.t_skin + gap
    a, b = 0.0, half_wall_at(p, y)          # bisect the outer limit
    if not in_cavity(p, a, y, gap):
        return None
    for _ in range(50):
        m = (a + b) / 2
        if in_cavity(p, m, y, gap):
            a = m
        else:
            b = m
    return (lo, a) if a > lo else None


def cavity_height(p: RingParams, width: float, gap: float = 0.0) -> float:
    """Radial height of the tallest centred rectangle of the given axial width."""
    lim = [cavity_limits(p, s * width / 2, gap) for s in (-1, 0, 1)]
    if any(v is None for v in lim):
        return 0.0
    return max(0.0, min(v[1] for v in lim) - max(v[0] for v in lim))


def outline(p: RingParams, n: int = 400) -> list[tuple[float, float]]:
    """Polygon of the band outline in (rho, y), found by marching rays from the centre."""
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        c, s = math.cos(a), math.sin(a)
        lo, hi = 0.0, p.half_width + p.half_wall + p.crown + 1
        for _ in range(50):
            m = (lo + hi) / 2
            if sdf(p, m * c, m * s) < 0:
                lo = m
            else:
                hi = m
        pts.append((lo * c, lo * s))
    return pts


def cavity_outline(p: RingParams, gap: float = 0.0, n: int = 120) -> list[tuple[float, float]]:
    """Polygon of the cavity in (rho, y)."""
    w = p.half_width - p.t_ti - gap
    ys = [-w + 2 * w * i / (n - 1) for i in range(n)]
    lim = [(y, cavity_limits(p, y, gap)) for y in ys]
    lim = [(y, v) for y, v in lim if v]
    return [(v[1], y) for y, v in lim] + [(v[0], y) for y, v in reversed(lim)]
