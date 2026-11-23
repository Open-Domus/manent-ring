"""What goes inside the ring and where.

The electronics sit on flat islands joined by bends of flex; the cell takes the rest
of the circle. Every part of the circuit in electrical/gen/design.py is assigned to an
island and a face, then packed in columns across the flex; the island is as long as its
fuller face. Angles: 90 deg is the back of the finger (LED and microphone), 0 deg is
the side facing the thumb (button), 270 deg is the palm side (cell).
"""
from dataclasses import dataclass, field, replace
from pathlib import Path

import math

import yaml

from electrical.gen.design import build as build_circuit
from electrical.gen.footprints import extent, footprint_of

ROOT = Path(__file__).resolve().parents[2]


def load_parts() -> dict:
    return yaml.safe_load((ROOT / "parts" / "parts.yaml").read_text())


@dataclass(frozen=True)
class Placed:
    part: str          # key in parts.yaml
    x: float           # centre along the island, mm from the island centre
    y: float           # axial centre, mm from the band centre
    face: str          # "out": towards the titanium, "in": towards the finger
    turned: bool = False   # True swaps length and width
    ref: str = ""          # reference in the circuit
    fp: str = ""           # footprint name


@dataclass(frozen=True)
class Island:
    name: str
    length: float                  # chord along the arc
    thickness: float               # board thickness on this island
    parts: tuple[Placed, ...] = field(default_factory=tuple)
    target_deg: tuple[float, float] | None = None   # where its centre must fall
    seat: str = "mid"              # "out": against the shell, "in": against the skin


FLEX_WIDTH = 5.6       # axial width of the flex
FLEX_T = 0.11          # two-layer flex between islands
STIFF_T = 0.20         # flex with stiffener
RIGID_T = 0.40         # four-layer rigid island for the fine-pitch parts
SOLDER = 0.05          # stand-off of a soldered part
BEND = 1.0             # length of each bend zone between islands
CELL_TABS = 3.0        # arc taken by the cell tabs and their joint
CLOSING_GAP = 1.0      # free arc left to close the loop
SWELL = 0.08           # cell thickness growth to allow for
CELL_GAP = 0.05        # insulating wrap between the swollen cell and the walls
BUTTON_DEG = 25.0      # where the button sits: the side of the finger, towards the thumb
PART_SPACING = 0.15    # between the land patterns of two parts on the same face
EDGE_MARGIN = 0.15     # from a land pattern to the edge of the board
# Extra room kept clear around the fine-pitch packages, for their tracks to fan out.
COURTYARD = {"soc": 0.3, "pmic": 0.3, "flash": 0.3, "mic": 0.2}

# name, board thickness, seat, shortest allowed length, where its centre must fall.
# Order along the arc, starting at the cell tabs: thumb side -> back of the finger -> far side.
ISLAND_SPECS = (
    # Charging and service pads face the finger; cell protection sits behind them.
    ("contacts", STIFF_T, "in", 3.0, None),
    ("button", STIFF_T, "out", 2.4, (-15.0, 30.0)),
    ("soc", RIGID_T, "mid", 0.0, None),
    ("audio", STIFF_T, "out", 0.0, (60.0, 120.0)),
    ("power", RIGID_T, "mid", 0.0, None),
    ("antenna", STIFF_T, "mid", 5.0, None),       # kept long: the antenna needs clear board
)
PROTECTION_NETS = {"CELL_P", "CELL_N", "SENSE", "VM", "PROT_CO", "PROT_DO", "FET_MID"}


def body_of(c) -> str | None:
    """Key in parts.yaml of the body that stands for a circuit component."""
    if c.sym.virtual or c.sym.name in ("PAD", "CELL"):
        return None
    by_value = {"nRF54L15": "soc", "nPM1304": "pmic", "W25Q128JW": "flash", "T5838": "mic", "S-82A1A": "protector"}
    by_symbol = {"SW": "button", "LED": "led", "ANTENNA": "antenna", "NMOS": "nfet"}
    if c.value in by_value:
        return by_value[c.value]
    if c.sym.name in by_symbol:
        return by_symbol[c.sym.name]
    if c.sym.name == "XTAL":
        return "xtal32m" if "MHz" in c.value else "xtal32k"
    if c.value == "2.2uH":
        return "inductor"
    return "passive0402" if c.fields.get("Package") == "0402" else "passive0201"


def home_of(c) -> tuple[str, str]:
    """Island and face of a circuit component."""
    nets = set(n for n in c.nets.values() if n)
    if c.sheet == "power":
        if nets & PROTECTION_NETS or c.sym.name == "TVS":
            return "contacts", "out"
        big = c.value in ("nPM1304", "2.2uH") or c.fields.get("Package") == "0402"
        return "power", "in" if big else "out"
    if c.sheet == "mcu_rf":
        if "ANT_FEED" in nets or c.value == "tune":
            return "antenna", "in"
        return "soc", "out" if "kHz" in c.value else "in"
    if c.sheet == "storage":
        return "soc", "out"
    if c.sheet == "audio":
        return "audio", "in"
    if c.sym.name == "SW":
        return "button", "out"
    if c.sym.name == "D":
        return "button", "in"
    return "audio", "out" if c.sym.name == "LED" else "in"


def pack(sizes: list[tuple[str, float, float]]) -> tuple[list[Placed], float]:
    """Pack land patterns (reference, length, width) in columns across the flex.

    Largest first; each goes, in the better of its two orientations, where it adds
    the least length. Returns the placements (x from the left edge of the pack,
    face left blank) and the packed length.
    """
    room = FLEX_WIDTH - 2 * EDGE_MARGIN
    cols: list[dict] = []
    for key, l, w in sorted(sizes, key=lambda s: -s[1] * s[2]):
        best = None
        for turned, (a, b) in ((False, (l, w)), (True, (w, l))):       # a along the arc, b across
            if b > room:
                continue
            for col in cols:
                if col["used"] + PART_SPACING + b <= room:
                    cost = max(0.0, a - col["width"])
                    if best is None or cost < best[0]:
                        best = (cost, col, turned, a, b)
            cost = a + PART_SPACING
            if best is None or cost < best[0]:
                best = (cost, None, turned, a, b)
        cost, col, turned, a, b = best
        if col is None:
            col = {"width": 0.0, "used": -PART_SPACING, "items": []}
            cols.append(col)
        col["items"].append((key, turned, a, b, col["used"] + PART_SPACING))
        col["used"] += PART_SPACING + b
        col["width"] = max(col["width"], a)
    placed, x = [], 0.0
    for col in cols:
        for key, turned, a, b, y0 in col["items"]:
            y = y0 + b / 2 - col["used"] / 2          # centre the column across the flex
            placed.append(Placed(key, x + col["width"] / 2, y, "", turned))
        x += col["width"] + PART_SPACING
    return placed, max(0.0, x - PART_SPACING)


PORT_OFFSET = 0.71     # microphone sound port, from the body centre along its length
PORT_KEEPOUT = 0.75    # from the port centre to the nearest land pattern on the other face


def _clear_of_ports(placed, room):
    """The microphone's port is a hole through the board: slide whatever sits on the
    other face across the band until it is clear of it."""
    ports = [(p.x, p.y - PORT_OFFSET) if p.turned else (p.x - PORT_OFFSET, p.y)
             for p in placed if p.part == "mic" and p.face == "in"]
    out = []
    for p in placed:
        if p.face == "out" and ports:
            (px, py), = ports
            l, w = room(p.ref)
            ex, ey = (w, l) if p.turned else (l, w)
            if abs(p.x - px) < ex / 2 + PORT_KEEPOUT and abs(p.y - py) < ey / 2 + PORT_KEEPOUT:
                side = 1 if py <= 0 else -1
                p = replace(p, y=py + side * (ey / 2 + PORT_KEEPOUT))
                assert abs(p.y) + ey / 2 <= FLEX_WIDTH / 2 - EDGE_MARGIN, "no room beside the port"
        out.append(p)
    return out


def build_islands() -> tuple[Island, ...]:
    parts = load_parts()["parts"]
    homes: dict[tuple[str, str], list] = {}
    body, fp = {}, {}

    def room(ref):      # the larger of land pattern and body, plus any fan-out room
        grow = 2 * COURTYARD.get(body[ref], 0.0)
        return tuple(max(e, b) + grow for e, b in zip(extent(fp[ref]), parts[body[ref]]["size"]))

    for c in build_circuit():
        if body_of(c):
            body[c.ref], fp[c.ref] = body_of(c), footprint_of(c)
            homes.setdefault(home_of(c), []).append(c.ref)
    islands = []
    for name, thickness, seat, shortest, target in ISLAND_SPECS:
        faces = {f: pack([(ref, *room(ref)) for ref in homes.pop((name, f), [])]) for f in ("in", "out")}
        length = max(shortest, max(l for _, l in faces.values()) + 2 * EDGE_MARGIN)
        placed = [Placed(body[p.part], p.x - l / 2, p.y, f, p.turned, p.part, fp[p.part])
                  for f, (ps, l) in faces.items() for p in ps]
        placed = tuple(_clear_of_ports(placed, room))
        islands.append(Island(name, math.ceil(length * 100 - 1e-9) / 100, thickness, placed, target, seat))
    assert not homes, f"parts assigned to unknown islands: {list(homes)}"
    return tuple(islands)


ISLANDS = build_islands()

DEFAULT_CELL = {"A": "grp160626", "B": "grp1707_29"}
