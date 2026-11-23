"""A small maze router for the ring board.

Reads electrical/out/pads.json (exact pad copper, from KiCad) and board.json (zones),
writes electrical/out/routes.json (tracks and vias). KiCad's rule check is the judge of
the result; this file only has to produce something for it to judge.

Construction assumed (see docs/fabricators.md):
  - every island is rigid, LAYERS copper layers, with laser microvias that may sit in a
    pad and may be stacked across any span of layers;
  - only the two FLEX layers continue through the bends between islands; the first of
    them is a ground plane from end to end, the second carries the signals across;
  - one track width and one clearance everywhere.
"""
import heapq
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "electrical" / "out"

G = 0.0375            # grid pitch, mm
TRACK = 0.075
CLEAR = 0.075
VIA_PAD, VIA_DRILL = 0.20, 0.10
HOLE_TO_HOLE = 0.20
EDGE = 0.15
SLACK = 0.03          # allowance for the grid when claiming room around copper
VIA_COST = 30.0       # in grid steps, per layer crossed
# Ball grids: (rows, columns). Each ring of balls, counted from the edge, leaves the chip
# one layer deeper, so that outer balls never wall in the inner ones.
PLANE_NET = "GND"
GRIDS = {"nRF54L15_CSP47": (7, 7), "nPM1304_CSP35": (5, 7)}
# On these packages a via touching a pad sits on its centre, or not on the pad at all.
CENTRE_ONLY = set(GRIDS) | {"W25Q128JW_WLCSP21"}
TRANSITION = 0.30     # no via this close to the line where an island ends and the flex begins
TAIL_LAYER = 0        # the test tail carries tracks on its pad layer only, and no vias


def disc(radius_mm: float) -> list[tuple[int, int]]:
    r = radius_mm / G
    n = int(math.floor(r))
    return [(dx, dy) for dx in range(-n, n + 1) for dy in range(-n, n + 1) if dx * dx + dy * dy <= r * r + 1e-9]


def dilate(mask: np.ndarray, offsets) -> np.ndarray:
    out = np.zeros_like(mask)
    h, w = mask.shape
    for dx, dy in offsets:
        ys0, ys1 = max(0, dy), min(h, h + dy)
        xs0, xs1 = max(0, dx), min(w, w + dx)
        out[ys0:ys1, xs0:xs1] |= mask[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out


class Board:
    def __init__(self, layers: int):
        self.layers = layers
        self.flex = (layers // 2 - 1, layers // 2)
        self.plane = self.flex[0]
        data = json.loads((OUT / "pads.json").read_text())
        board = json.loads((OUT / "board.json").read_text())
        self.zones, cut_y = board["zones"], board["tail_cut"][2]
        pts = [(s[0], s[1]) for s in data["edge"]] + [(s[2], s[3]) for s in data["edge"]]
        self.x0, self.y0 = min(p[0] for p in pts) - 4 * G, min(p[1] for p in pts) - 4 * G
        self.w = int((max(p[0] for p in pts) - self.x0) / G) + 5
        self.h = int((max(p[1] for p in pts) - self.y0) / G) + 5
        self.hw = self.h * self.w
        self.gx = self.x0 + G * np.arange(self.w)
        self.gy = self.y0 + G * np.arange(self.h)

        inside = self.raster([self.chain(data["edge"])], 0, self.h, 0, self.w)
        # A little more than the rule: diagonal steps cut inside corners of the outline.
        keep = ~dilate(~inside, disc(EDGE + TRACK / 2 + SLACK + 0.025))
        self.allowed = np.repeat(keep[None], layers, axis=0)
        self.novia = np.zeros((layers, self.h, self.w), bool)
        for z in self.zones:
            if z["kind"] == "bend":
                a, b = self.ix(z["x0"] - 0.1), self.ix(z["x1"] + 0.1) + 1
                for l in range(layers):
                    if l not in self.flex:
                        self.allowed[l, :, a:b] = False
                self.novia[:, :, self.ix(z["x0"] - TRANSITION):self.ix(z["x1"] + TRANSITION) + 1] = True
        # The tail is cut off after the test: nothing but the stubs to its own pads may be there.
        self.tail = inside & (self.gy[:, None] > cut_y - G / 2)
        for l in range(layers):
            if l != TAIL_LAYER:
                self.allowed[l][self.tail] = False
        self.novia[:, self.tail] = True
        self.claim = np.zeros((layers, self.h, self.w), np.int32)
        self.nohole = np.zeros((layers, self.h, self.w), bool)      # no new hole here
        self.nohole_grid = np.zeros((layers, self.h, self.w), bool) # same, for holes in grid-package pads
        self.grid_cells = np.zeros((self.h, self.w), bool)
        footprint = {p["ref"]: p["footprint"] for p in board["parts"]}

        self.net_id, self.pads = {}, []
        for i, p in enumerate(data["pads"]):
            if p["kind"] == "hole":
                self.block_disc(p["x"], p["y"], p["d"] / 2 + EDGE + TRACK / 2 + SLACK)
                continue
            name = p["net"] if p["net"] and not p["net"].startswith("unconnected-") else f"~{i}"
            net = self.net_id.setdefault(name, len(self.net_id) + 1)
            layer = 0 if p["side"] == "F" else layers - 1
            xs = [q[0] for r in p["rings"] for q in r]
            ys = [q[1] for r in p["rings"] for q in r]
            x_a, x_b = max(0, self.ix(min(xs)) - 1), min(self.w, self.ix(max(xs)) + 2)
            y_a, y_b = max(0, self.iy(min(ys)) - 1), min(self.h, self.iy(max(ys)) + 2)
            m = self.raster(p["rings"], y_a, y_b, x_a, x_b)
            cy, cx = self.iy(p["y"]), self.ix(p["x"])
            if not m.any() or p["ref"].startswith("U") or p["ref"].startswith("MK"):
                m[min(max(cy - y_a, 0), m.shape[0] - 1), min(max(cx - x_a, 0), m.shape[1] - 1)] = True
            full = np.zeros((self.h, self.w), bool)
            full[y_a:y_b, x_a:x_b] = m
            # Grid-package pads sit on the grid; the others get a little more allowance.
            extra = 0.0 if footprint.get(p["ref"]) in GRIDS else 0.01
            self.add_claim(layer, dilate(full, disc(TRACK / 2 + CLEAR + SLACK + extra)), net)
            # Tracks may end only where they stay inside the pad: one cell in from its edge.
            core = ~dilate(~full, disc(G))
            if not core.any():
                core[min(max(cy, 0), self.h - 1), min(max(cx, 0), self.w - 1)] = True
            cells = np.flatnonzero(core) + layer * self.hw
            ring = 0
            grid = GRIDS.get(footprint.get(p["ref"]))
            if grid and len(p["pad"]) == 2:
                r, c = ord(p["pad"][0]) - 65, int(p["pad"][1]) - 1
                ring = min(r, c, grid[0] - 1 - r, grid[1] - 1 - c)
            centred = footprint.get(p["ref"]) in CENTRE_ONLY
            if centred:
                self.grid_cells[cy, cx] = True
                spot = np.zeros((self.h, self.w), bool)
                spot[cy, cx] = True
                near = dilate(spot, disc((max(xs) - min(xs)) / 2 + VIA_PAD / 2 + G))
                # Outer balls of a ball grid leave on the surface: a via there would wall in the
                # ring behind it. Every other ball may take a via on its centre.
                near[cy, cx] = bool(grid) and ring == 0
                self.novia[layer] |= near
            self.pads.append({"ref": p["ref"], "pad": p["pad"], "net": net, "name": name, "layer": layer,
                              "x": p["x"], "y": p["y"], "cells": cells, "ring": ring, "cy": cy, "cx": cx,
                              "grid": centred, "tail": p["y"] > cut_y})
        self.names = {v: k for k, v in self.net_id.items()}

    def ix(self, x): return int(round((x - self.x0) / G))
    def iy(self, y): return int(round((y - self.y0) / G))

    @staticmethod
    def chain(segments):
        """Order loose outline segments into one ring."""
        segs = [((round(s[0], 4), round(s[1], 4)), (round(s[2], 4), round(s[3], 4))) for s in segments]
        ring = [segs[0][0], segs[0][1]]
        rest = segs[1:]
        while rest:
            for s in rest:
                if s[0] == ring[-1]:
                    ring.append(s[1])
                elif s[1] == ring[-1]:
                    ring.append(s[0])
                else:
                    continue
                rest.remove(s)
                break
            else:
                raise ValueError("outline is not closed")
        return ring

    def raster(self, rings, y_a, y_b, x_a, x_b) -> np.ndarray:
        """Even-odd fill of polygon rings on the cell centres of a window."""
        X, Y = np.meshgrid(self.gx[x_a:x_b], self.gy[y_a:y_b])
        inside = np.zeros(X.shape, bool)
        for ring in rings:
            for (xa, ya), (xb, yb) in zip(ring, ring[1:] + ring[:1]):
                if ya == yb:
                    continue
                cross = ((ya > Y) != (yb > Y)) & (X < (xb - xa) * (Y - ya) / (yb - ya) + xa)
                inside ^= cross
        return inside

    def add_claim(self, layer, mask, net):
        c = self.claim[layer]
        c[mask & (c != 0) & (c != net)] = -1
        c[mask & (c == 0)] = net

    def block_disc(self, x, y, r, layers=None):
        m = np.zeros((self.h, self.w), bool)
        m[min(self.iy(y), self.h - 1), min(self.ix(x), self.w - 1)] = True
        m = dilate(m, disc(r))
        for l in (range(self.layers) if layers is None else layers):
            self.allowed[l][m] = False

    def block_rect(self, x, y, half_x, half_y, layer):
        self.allowed[layer, self.iy(y - half_y):self.iy(y + half_y) + 1, self.ix(x - half_x):self.ix(x + half_x) + 1] = False


NB = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
      (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]


class Router:
    """Routes net by net. When a connection is walled in by earlier nets, those nets are
    ripped out, the connection is made, and they go back in the queue."""

    MAX_RIPS = 25

    def __init__(self, board: Board):
        self.b = board
        self.track_claim = disc(TRACK + CLEAR + SLACK)
        self.via_claim = disc(VIA_PAD / 2 + TRACK / 2 + CLEAR + SLACK)
        # A via needs clear cells two steps around it. On the pad centres of a grid package one
        # step is all there is, and all it needs: the via has exactly the room of the pad itself.
        self.via_fit = disc(2 * G)
        self.via_fit_grid = disc(VIA_PAD / 2 - TRACK / 2)
        # Holes keep their distance with the grid allowance, except between the pads of a grid
        # package: those vias sit exactly on the pad centres, 0.3 mm apart, which is the limit.
        self.hole_keep = disc(VIA_DRILL + HOLE_TO_HOLE + SLACK)
        self.hole_keep_grid = disc(VIA_DRILL + HOLE_TO_HOLE - 0.01)
        self.near = disc(VIA_PAD / 2)
        self.fan_vias, self.records, self.claimed = [], {}, {}
        self.failed, self.rips, self.seen = {}, {}, {}
        self.tail_open = False              # True only while a tail pad is being connected

    # ---- copper bookkeeping -------------------------------------------------------
    def stamp_via(self, net, y, x, l1, l2):
        b = self.b
        stamp = np.zeros((b.h, b.w), bool)
        stamp[y, x] = True
        claim, keep = dilate(stamp, self.via_claim), dilate(stamp, self.hole_keep)
        keep_grid = dilate(stamp, self.hole_keep_grid) if b.grid_cells[y, x] else keep
        cells = np.flatnonzero(claim | keep)
        for l in range(l1, l2 + 1):
            b.add_claim(l, claim, net)
            b.nohole[l] |= keep
            b.nohole_grid[l] |= keep_grid
            b.nohole[l, y, x] = b.nohole_grid[l, y, x] = False   # its own net may stack on the same hole
            self.claimed.setdefault(net, set()).update((cells + l * b.hw).tolist())

    def stamp_track(self, net, layer, run):
        b = self.b
        ys, xs = [c[0] for c in run], [c[1] for c in run]
        y_a, y_b = max(0, min(ys) - 6), min(b.h, max(ys) + 7)
        x_a, x_b = max(0, min(xs) - 6), min(b.w, max(xs) + 7)
        win = np.zeros((y_b - y_a, x_b - x_a), bool)
        win[np.array(ys) - y_a, np.array(xs) - x_a] = True
        grown = np.zeros((b.h, b.w), bool)
        grown[y_a:y_b, x_a:x_b] = dilate(win, self.track_claim)
        b.add_claim(layer, grown, net)
        self.claimed.setdefault(net, set()).update((np.flatnonzero(grown) + layer * b.hw).tolist())

    def rebuild(self):
        b = self.b
        b.claim[:] = self.base_claim
        b.nohole[:], b.nohole_grid[:] = self.base_nohole
        self.claimed = {}
        for net, recs in self.records.items():
            for rec in recs:
                (self.stamp_via if rec[0] == "via" else self.stamp_track)(net, *rec[1:])

    def fan_out(self):
        """Drop each inner ball of a grid package to its ring's layer before routing."""
        b = self.b
        used = {n for n in b.names if sum(p["net"] == n for p in b.pads) > 1}
        for p in b.pads:
            if p["ring"] and p["net"] in used:
                deep = p["layer"] - p["ring"] if p["layer"] else p["ring"]
                l1, l2 = min(p["layer"], deep), max(p["layer"], deep)
                self.stamp_via(p["net"], p["cy"], p["cx"], l1, l2)
                self.fan_vias.append((p["net"], p["cy"], p["cx"], l1, l2))
                p["cells"] = np.array([l * b.hw + p["cy"] * b.w + p["cx"] for l in range(l1, l2 + 1)])
        self.base_claim, self.base_nohole = b.claim.copy(), (b.nohole.copy(), b.nohole_grid.copy())
        self.claimed = {}

    # ---- searching -----------------------------------------------------------------
    def maps(self, net, claim, nohole):
        b = self.b
        ok = b.allowed & ((claim == 0) | (claim == net))
        if not self.tail_open:
            ok[:, b.tail] = False
        free = ~np.where(b.grid_cells[None], nohole[1], nohole[0]) & ~b.novia
        via = np.stack([np.where(b.grid_cells, ~dilate(~ok[l], self.via_fit_grid), ~dilate(~ok[l], self.via_fit))
                        for l in range(b.layers)]) & free
        plane = (ok[b.plane] & ~b.tail).tobytes()
        ok[b.plane] = False                 # the plane layer takes vias, not tracks
        return ok.tobytes(), bytearray(via.tobytes()), plane

    def search(self, sources, goal, okb, viab, target, done=None):
        b = self.b
        w, hw, layers = b.w, b.hw, b.layers
        tx, ty, tl = b.ix(target["x"]), b.iy(target["y"]), target["layer"]

        def heur(idx):
            l, rem = divmod(idx, hw)
            y, x = divmod(rem, w)
            dx, dy = abs(x - tx), abs(y - ty)
            return max(dx, dy) + 0.4142 * min(dx, dy) + VIA_COST * abs(l - tl)

        dist, prev, heap = {}, {}, []
        for s in sources:
            dist[s] = 0.0
            heap.append((heur(s), 0.0, s))
        heapq.heapify(heap)
        hmax, wmax = b.h - 1, w - 1
        self.seen = dist                    # kept for diagnosis: what the last search reached
        while heap:
            _, gc, idx = heapq.heappop(heap)
            if gc > dist[idx]:
                continue
            if (done(idx) if done else idx in goal):
                path = [idx]
                while idx in prev:
                    idx = prev[idx]
                    path.append(idx)
                return path[::-1]
            l, rem = divmod(idx, hw)
            y, x = divmod(rem, w)
            for dx, dy, c in NB:
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx > wmax or ny > hmax:
                    continue
                n = idx + dy * w + dx
                if not okb[n] and (goal is None or n not in goal):
                    continue
                ng = gc + c
                if ng < dist.get(n, 1e18):
                    dist[n] = ng
                    prev[n] = idx
                    heapq.heappush(heap, (ng + heur(n), ng, n))
            if viab[idx]:
                for dl in (-1, 1):
                    if 0 <= l + dl < layers:
                        n = idx + dl * hw
                        if viab[n]:
                            ng = gc + VIA_COST
                            if ng < dist.get(n, 1e18):
                                dist[n] = ng
                                prev[n] = idx
                                heapq.heappush(heap, (ng + heur(n), ng, n))
        return None

    def spaced(self, sources, goal, okb, viab, target, done):
        """Search, and search again while two vias of the path itself are too close."""
        b = self.b
        for _ in range(12):
            path = self.search(sources, goal, okb, viab, target, done)
            if path is None:
                return None
            vias, k = [], 0
            while k + 1 < len(path):
                if path[k + 1] // b.hw != path[k] // b.hw:
                    j = k + 1
                    while j + 1 < len(path) and path[j + 1] % b.hw == path[k] % b.hw:
                        j += 1
                    y, x = divmod(path[k] % b.hw, b.w)
                    vias.append((y, x, min(path[k] // b.hw, path[j] // b.hw), max(path[k] // b.hw, path[j] // b.hw)))
                    k = j
                else:
                    k += 1
            limit = ((VIA_DRILL + HOLE_TO_HOLE + SLACK) / G) ** 2
            clash = [(u, v) for i, u in enumerate(vias) for v in vias[i + 1:]
                     if u[2] <= v[3] and v[2] <= u[3] and (u[0] - v[0]) ** 2 + (u[1] - v[1]) ** 2 < limit]
            if not clash:
                return path
            (y, x, l1, l2), other = clash[0]
            for dx, dy in self.hole_keep:       # no second via near the first one
                if (dx or dy) and 0 <= y + dy < b.h and 0 <= x + dx < b.w:
                    for l in range(b.layers):
                        viab[l * b.hw + (y + dy) * b.w + x + dx] = 0
        return None

    def connect(self, net, sources, goal, target, done=None):
        """Find a path; if earlier nets wall it in, rip them out. Returns (path, ripped)."""
        b = self.b
        okb, viab, plane = self.maps(net, b.claim, (b.nohole, b.nohole_grid))
        lo = b.plane * b.hw
        if done == "plane":
            done = lambda i, p=plane: lo <= i < lo + b.hw and p[i - lo]
        path = self.spaced(sources, goal, okb, viab, target, done)
        if path is not None:
            return path, []
        # Against the bare board, but still clear of the holes this net already has.
        holes = [h.copy() for h in self.base_nohole]
        for rec in self.records.get(net, []):
            if rec[0] == "via":
                _, y, x, l1, l2 = rec
                stamp = np.zeros((b.h, b.w), bool)
                stamp[y, x] = True
                keep = dilate(stamp, self.hole_keep)
                keep[y, x] = False
                for l in range(l1, l2 + 1):
                    holes[0][l] |= keep
                    holes[1][l] |= keep
        okb, viab, plane = self.maps(net, self.base_claim, holes)
        if done is not None:
            done = lambda i, p=plane: lo <= i < lo + b.hw and p[i - lo]
        path = self.spaced(sources, goal, okb, viab, target, done)
        if path is None:
            return None, []
        touched = set()
        for i in path:
            l, rem = divmod(i, b.hw)
            y, x = divmod(rem, b.w)
            for dx, dy in self.near:
                if 0 <= x + dx < b.w and 0 <= y + dy < b.h:
                    touched.add(i + dy * b.w + dx)
        blockers = [m for m, cells in self.claimed.items() if m != net and not cells.isdisjoint(touched)]
        if not blockers or any(self.rips.get(m, 0) >= self.MAX_RIPS for m in blockers):
            return None, []
        for m in blockers:
            self.rips[m] = self.rips.get(m, 0) + 1
            del self.records[m]
        self.rebuild()
        return path, blockers

    # ---- routing -------------------------------------------------------------------
    def route_net(self, net: int) -> list[int]:
        """Route one net from scratch. Returns the nets ripped out on the way."""
        b = self.b
        self.records[net] = []
        self.failed.pop(net, None)
        pads = [p for p in b.pads if p["net"] == net]
        ripped = []
        if b.names[net] == PLANE_NET:
            for p in pads:
                self.tail_open = p["tail"]
                path, out = self.connect(net, set(p["cells"].tolist()), None,
                                         {"x": p["x"], "y": p["y"], "layer": b.plane}, done="plane")
                self.tail_open = False
                ripped += out
                if path is None:
                    self.failed.setdefault(net, []).append((p["ref"], p["pad"]))
                elif len(path) > 1:
                    self.commit(net, path)
            return ripped
        # Pads on the test tail are leaves: the net is routed without them, then each gets a
        # stub. Nothing else may run through the tail, and no stub may feed another pad.
        main, leaves = [p for p in pads if not p["tail"]], [p for p in pads if p["tail"]]
        done, todo = [main[0]], main[1:]
        tree = set(main[0]["cells"].tolist())
        tail_cells = set(np.flatnonzero(b.tail).tolist())
        for stage in (todo, leaves):
            self.tail_open = stage is leaves
            while stage:
                target = min(stage, key=lambda p: min((p["x"] - d["x"]) ** 2 + (p["y"] - d["y"]) ** 2 for d in done))
                goal = {c: p for p in ([target] if self.tail_open else stage) for c in p["cells"].tolist()}
                path, out = self.connect(net, tree, goal, target)
                ripped += out
                if path is None:
                    self.failed.setdefault(net, []).append((target["ref"], target["pad"]))
                    stage.remove(target)
                    continue
                reached = goal[path[-1]]
                self.commit(net, path)
                if not self.tail_open:
                    tree.update(path)
                    tree.update(reached["cells"].tolist())
                    done.append(reached)
                else:
                    tree.update(i for i in path if i % b.hw not in tail_cells)
                stage.remove(reached)
        self.tail_open = False
        return ripped

    def commit(self, net, path):
        b = self.b
        nodes = [(i // b.hw, (i % b.hw) // b.w, i % b.w) for i in path]
        k = 0
        while k < len(nodes):
            j = k
            while j + 1 < len(nodes) and nodes[j + 1][0] == nodes[k][0]:
                j += 1
            if j > k:
                rec = ("track", nodes[k][0], [(y, x) for _, y, x in nodes[k:j + 1]])
                self.records[net].append(rec)
                self.stamp_track(net, *rec[1:])
            if j + 1 < len(nodes):          # a layer change: follow it to the end of the stack
                m = j + 1
                while m + 1 < len(nodes) and nodes[m + 1][1:] == nodes[j][1:]:
                    m += 1
                l1, l2 = sorted((nodes[j][0], nodes[m][0]))
                rec = ("via", nodes[j][1], nodes[j][2], l1, l2)
                self.records[net].append(rec)
                self.stamp_via(net, *rec[1:])
                k = m
            else:
                k = j + 1

    def result(self) -> dict:
        b = self.b
        cell = lambda y, x: (round(b.x0 + x * G, 4), round(b.y0 + y * G, 4))
        # A via on the centre of a grid-package pad sits exactly on that pad.
        exact = {(p["cy"], p["cx"]): (p["x"], p["y"]) for p in b.pads if p["grid"]}
        pos = lambda y, x: exact.get((y, x), cell(y, x))
        tracks, stacks = [], {}
        used = {}                           # (net, y, x) -> layers that copper of the net reaches there
        for net, recs in self.records.items():
            for rec in recs:
                if rec[0] == "via":
                    _, y, x, l1, l2 = rec
                    stacks.setdefault((net, y, x), []).append((l1, l2))
                    used.setdefault((net, y, x), set()).update((l1, l2))
                else:
                    _, layer, run = rec
                    for y, x in (run[0], run[-1]):
                        used.setdefault((net, y, x), set()).add(layer)
                    pts = [run[0]]
                    for a, c, d in zip(run, run[1:], run[2:]):
                        if (c[0] - a[0], c[1] - a[1]) != (d[0] - c[0], d[1] - c[1]):
                            pts.append(c)
                    pts.append(run[-1])
                    xy = [list(cell(y, x)) for y, x in pts]
                    for k in (0, -1):       # ends on a grid-package pad go to its exact centre
                        if pts[k] in exact:
                            xy[k] = list(exact[pts[k]])
                    tracks.append({"net": b.names[net], "layer": layer, "pts": xy})
        # Fan-out vias: keep only the part of each stack that something uses.
        pad_layer = {(p["net"], p["cy"], p["cx"]): p["layer"] for p in b.pads}
        for net, y, x, l1, l2 in self.fan_vias:
            reach = used.get((net, y, x), set()) | {pad_layer[(net, y, x)]}
            if len(reach) > 1:
                stacks.setdefault((net, y, x), []).append((min(reach), max(reach)))
        vias = []
        for (net, y, x), spans in stacks.items():
            spans.sort()
            merged = [list(spans[0])]
            for l1, l2 in spans[1:]:
                if l1 <= merged[-1][1]:
                    merged[-1][1] = max(merged[-1][1], l2)
                else:
                    merged.append([l1, l2])
            for l1, l2 in merged:
                vias.append({"net": b.names[net], "x": pos(y, x)[0], "y": pos(y, x)[1], "l1": l1, "l2": l2})
        failed = [[b.names[n], *f] for n, fs in self.failed.items() for f in fs]
        return {"layers": b.layers, "track": TRACK, "via_pad": VIA_PAD, "via_drill": VIA_DRILL, "clearance": CLEAR,
                "plane": {"net": PLANE_NET, "layer": b.plane}, "tracks": tracks, "vias": vias, "failed": failed}


def order(board: Board, rng) -> list[int]:
    """Shortest nets first, ground last; a little shuffling makes each attempt different."""
    def span(net):
        ps = [p for p in board.pads if p["net"] == net]
        return (max(p["x"] for p in ps) - min(p["x"] for p in ps)) + (max(p["y"] for p in ps) - min(p["y"] for p in ps))
    nets = [n for n in board.names if sum(p["net"] == n for p in board.pads) > 1]
    return sorted(nets, key=lambda n: (board.names[n] == PLANE_NET, span(n) * rng.uniform(0.7, 1.3)))


def attempt(layers: int, seed: int) -> dict:
    t = time.time()
    rng = np.random.default_rng(seed)
    board = Board(layers)
    for part in json.loads((OUT / "board.json").read_text())["parts"]:
        if part["footprint"] == "EVPBB":       # no copper under the switch body
            hx, hy = (0.8, 1.0) if part["rot"] else (1.0, 0.8)   # the body between its lands
            board.block_rect(part["x"], part["y"], hx, hy, 0 if part["side"] == "F" else layers - 1)
    r = Router(board)
    r.fan_out()
    queue, rips = order(board, rng), 0
    while queue:
        net = queue.pop(0)
        out = r.route_net(net)
        rips += len(out)
        for m in out:                       # ripped nets go back in, ahead of ground
            if m in queue:
                queue.remove(m)
        ground = [n for n in queue if board.names[n] == PLANE_NET]
        queue = [n for n in queue if board.names[n] != PLANE_NET] + out + ground
    res = r.result()
    res["seed"] = seed
    print(f"seed {seed}: {layers} layers, {len(res['tracks'])} tracks, {len(res['vias'])} vias, {rips} rip-ups, "
          f"{len(res['failed'])} connections failed, {time.time() - t:.0f} s", flush=True)
    return res


def run(layers: int, seeds=(4, 5, 1, 2, 3, 6)):
    best = None
    for seed in seeds:
        res = attempt(layers, seed)
        if best is None or len(res["failed"]) < len(best["failed"]):
            best = res
        if not best["failed"]:
            break
    (OUT / "routes.json").write_text(json.dumps(best))
    for f in best["failed"]:
        print("  not routed:", *f)
    return best


if __name__ == "__main__":
    run(json.loads((OUT / "board.json").read_text())["layers"],
        seeds=[int(a) for a in sys.argv[1:]] or (4, 5, 1, 2, 3, 6))
