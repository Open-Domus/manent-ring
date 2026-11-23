"""What goes inside the ring and where.

The electronics sit on flat islands joined by bends of flex; the cell takes the rest
of the circle. Angles: 90 deg is the back of the finger (LED and microphone), 0 deg is
the side facing the thumb (button), 270 deg is the palm side (cell).
"""
from dataclasses import dataclass, field
from pathlib import Path

import yaml

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
CELL_CENTRE_DEG = 255.0  # palm side, turned so that the button lands on the thumb side

# Order along the arc, starting just after the cell and going thumb side -> back -> far side.
ISLANDS: tuple[Island, ...] = (
    Island("protection", 3.0, STIFF_T, (
        Placed("protector", 0.0, 1.2, "in"),
        Placed("passive0201", -0.6, -1.2, "in"),
        Placed("passive0201", 0.6, -1.2, "in"),
    )),
    Island("button", 3.4, STIFF_T, (
        Placed("button", 0.0, 0.0, "out"),
    ), target_deg=(-15.0, 30.0), seat="out"),
    Island("soc", 4.4, RIGID_T, (
        Placed("soc", -0.6, 1.2, "in"),
        Placed("xtal32m", -0.9, -1.5, "in"),
        Placed("passive0201", 1.2, 2.0, "in"),
        Placed("passive0201", 1.2, 1.2, "in"),
        Placed("passive0201", 1.2, 0.4, "in"),
        Placed("passive0201", 0.6, -1.0, "in"),
        Placed("passive0201", 0.6, -2.0, "in"),
        Placed("passive0402", 1.6, -1.5, "in", turned=True),
        Placed("flash", 0.0, 0.0, "out"),
    )),
    Island("audio", 4.5, STIFF_T, (
        Placed("mic", 0.0, 0.9, "in"),
        Placed("led", 0.0, -1.9, "out"),
        Placed("passive0201", -1.2, -1.9, "in"),
        Placed("passive0201", 1.2, -1.9, "in"),
    ), target_deg=(60.0, 120.0), seat="out"),
    Island("power", 5.0, RIGID_T, (
        Placed("pmic", -0.7, 1.0, "in"),
        Placed("inductor", -0.9, -1.6, "in"),
        Placed("passive0402", 1.6, 1.6, "in", turned=True),
        Placed("passive0402", 1.6, 0.2, "in", turned=True),
        Placed("passive0402", 1.6, -1.2, "in", turned=True),
        Placed("passive0201", 0.6, -1.6, "in"),
    )),
    Island("antenna", 5.0, STIFF_T, (
        Placed("antenna", 0.0, 2.2, "in"),
        Placed("passive0201", -1.6, 2.2, "in"),
        Placed("passive0201", 1.6, 2.2, "in"),
    )),
    # Three charging pads (ground, positive, ground) across the width and two service
    # pads; they reach the inner surface through the resin, so no part body is checked.
    Island("contacts", 3.4, STIFF_T, seat="in"),
)

DEFAULT_CELL = {"A": "grp160626", "B": "grp1707_29"}
