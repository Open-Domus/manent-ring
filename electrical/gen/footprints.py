"""Footprints: the project library in electrical/kicad/manent.pretty.

Standard chip parts are copies of KiCad's stock footprints. The others are written here
from the manufacturers' land-pattern drawings; `status` says how far each was checked.
Every footprint has its long side along X.
"""
import re
from functools import lru_cache
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "kicad" / "manent.pretty"
LIB_NAME = "manent"


def _grid(rows: str, cols: int, px: float, py: float, skip=(), only=None):
    """Ball positions for a grid named A1.. with A1 at the top left, seen from above."""
    out = {}
    for r, row in enumerate(rows):
        for c in range(cols):
            name = f"{row}{c + 1}"
            if name in skip or (only is not None and name not in only):
                continue
            out[name] = (round((c - (cols - 1) / 2) * px, 4), round((r - (len(rows) - 1) / 2) * py, 4))
    return out


def _balls(positions, d):
    return [(n, "circle", x, y, d, d) for n, (x, y) in positions.items()]


W25Q_BALLS = "A2 A5 A6 B1 B3 B4 B6 C1 C3 C4 C6 D1 D3 D4 D6 E1 E3 E4 E6 F2 F5".split()

# name: body (x, y), pads [(number, shape, x, y, w, h)], extras, status
CUSTOM = {
    "nRF54L15_CSP47": dict(
        body=(2.45, 2.25), pads=_balls(_grid("ABCDEFG", 7, 0.3, 0.3, skip=("B2", "C1")), 0.20), mask=0.025,
        status="ball map verified; pad diameter derived from Nordic's reference layout notes; "
               "array assumed centred on the body"),
    "nPM1304_CSP35": dict(
        body=(3.08, 2.38), pads=_balls(_grid("ABCDE", 7, 0.419, 0.44), 0.22), mask=0.025,
        status="ball map verified; which pitch runs along which side is not confirmed"),
    "W25Q128JW_WLCSP21": dict(
        body=(3.4, 3.0), pads=_balls(_grid("ABCDEF", 6, 0.5, 0.5, only=W25Q_BALLS), 0.25), mask=0.025,
        status="ball positions verified (6 x 6 grid, 0.5 mm); body size not published, estimated"),
    # TDK DS-000383 figure 36, moved so that the origin is the body centre (port at +0.71).
    "T5838": dict(
        body=(3.5, 2.65),
        pads=[("7", "rect", -1.364, -0.8375, 0.522, 0.725), ("6", "rect", -0.542, -0.8375, 0.522, 0.725),
              ("1", "rect", -1.364, 0.8375, 0.522, 0.725), ("2", "rect", -0.542, 0.8375, 0.522, 0.725),
              ("5", "rect", 1.475, -1.05, 0.30, 0.30), ("4", "rect", 1.475, 1.05, 0.30, 0.30)],
        ring=("3", 0.71, 0.0, 1.025, 1.625), hole=(0.71, 0.0, 0.6),
        status="pad sizes and positions verified; pin-to-pad mapping read by matching two figures"),
    # Panasonic ANCTB13E land pattern plan. A and A' are one terminal, B and B' the other.
    "EVPBB": dict(
        body=(2.6, 1.6),
        pads=[("1", "rect", -1.325, -0.375, 0.55, 0.55), ("1", "rect", -1.325, 0.375, 0.55, 0.55),
              ("2", "rect", 1.325, -0.375, 0.55, 0.55), ("2", "rect", 1.325, 0.375, 0.55, 0.55)],
        status="land sizes read from the drawing; keep the area under the body free of copper and vias"),
    # ABLIC PV006-A-L-SD-1.0.
    "DFN-6_1414": dict(
        body=(1.4, 1.4),
        pads=[("1", "rect", -0.5, 0.625, 0.2, 0.55), ("2", "rect", 0.0, 0.625, 0.2, 0.55), ("3", "rect", 0.5, 0.625, 0.2, 0.55),
              ("4", "rect", 0.5, -0.625, 0.2, 0.55), ("5", "rect", 0.0, -0.625, 0.2, 0.55), ("6", "rect", -0.5, -0.625, 0.2, 0.55),
              ("", "rect", 0.0, 0.0, 0.8, 0.15)],
        status="land sizes verified; pin order around the package assumed"),
    "Crystal_1612_4Pad": dict(
        body=(1.6, 1.2),
        pads=[("1", "rect", -0.55, 0.4, 0.5, 0.4), ("", "rect", 0.55, 0.4, 0.5, 0.4),
              ("2", "rect", 0.55, -0.4, 0.5, 0.4), ("", "rect", -0.55, -0.4, 0.5, 0.4)],
        status="generic pattern, not from the Kyocera drawing; the two lid pads are left unconnected"),
    "Antenna_1608": dict(
        body=(1.6, 0.8), pads=[("1", "rect", -0.6, 0.0, 0.4, 0.8), ("", "rect", 0.6, 0.0, 0.4, 0.8)],
        status="placeholder until the antenna is chosen"),
    "Pad_Charge_D1.5": dict(body=(1.5, 1.5), pads=[("1", "circle", 0, 0, 1.5, 1.5)], paste=False, status="design choice"),
    "Pad_Service_D0.8": dict(body=(0.8, 0.8), pads=[("1", "circle", 0, 0, 0.8, 0.8)], paste=False, status="design choice"),
    "Pad_Test_D1.0": dict(body=(1.0, 1.0), pads=[("1", "circle", 0, 0, 1.0, 1.0)], paste=False, status="design choice"),
    "Cell_Tabs": dict(
        body=(2.4, 4.6), pads=[("1", "rect", 0.0, -1.3, 1.6, 1.8), ("2", "rect", 0.0, 1.3, 1.6, 1.8)], paste=False,
        status="placeholder until the cell drawing is in hand"),
}


def _text(name: str, fp: dict) -> str:
    bx, by = fp["body"][0] / 2, fp["body"][1] / 2
    layers = '"F.Cu" "F.Mask" "F.Paste"' if fp.get("paste", True) else '"F.Cu" "F.Mask"'
    mask = f' (solder_mask_margin {fp["mask"]})' if "mask" in fp else ""
    out = [f'(footprint "{name}" (version 20241229) (generator "manent_gen") (layer "F.Cu")',
           f'\t(descr "{fp["status"]}")',
           '\t(property "Reference" "REF**" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 0.3 0.3) (thickness 0.05))))',
           f'\t(property "Value" "{name}" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 0.3 0.3) (thickness 0.05))))',
           '\t(attr smd)',
           f'\t(fp_rect (start {-bx} {-by}) (end {bx} {by}) (stroke (width 0.05) (type solid)) (fill no) (layer "F.Fab"))']
    ex, ey = extent_of(fp)
    out.append(f'\t(fp_rect (start {-ex / 2 - 0.05:.3f} {-ey / 2 - 0.05:.3f}) (end {ex / 2 + 0.05:.3f} {ey / 2 + 0.05:.3f}) '
               '(stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))')
    for num, shape, x, y, w, h in fp["pads"]:
        out.append(f'\t(pad "{num}" smd {shape} (at {x} {y}) (size {w} {h}) (layers {layers}){mask})')
    if "ring" in fp:        # annular ground pad around the sound port, drawn as a thick circle
        num, x, y, d_in, d_out = fp["ring"]
        r, width = (d_in + d_out) / 4, (d_out - d_in) / 2
        out.append(f'\t(pad "{num}" smd custom (at {x - r} {y}) (size {width} {width}) (layers "F.Cu" "F.Mask" "F.Paste")'
                   f' (options (clearance outline) (anchor circle))'
                   f' (primitives (gr_circle (center {r} 0) (end {2 * r} 0) (width {width}) (fill no))))')
    if "hole" in fp:
        x, y, d = fp["hole"]
        out.append(f'\t(pad "" np_thru_hole circle (at {x} {y}) (size {d} {d}) (drill {d}) (layers "*.Cu" "*.Mask"))')
    return "\n".join(out) + "\n)\n"


def extent_of(fp: dict) -> tuple[float, float]:
    xs = [fp["body"][0] / 2] + [abs(x) + w / 2 for _, _, x, _, w, _ in fp["pads"]]
    ys = [fp["body"][1] / 2] + [abs(y) + h / 2 for _, _, _, y, _, h in fp["pads"]]
    if "ring" in fp:
        _, x, y, _, d = fp["ring"]
        xs.append(abs(x) + d / 2), ys.append(abs(y) + d / 2)
    return 2 * max(xs), 2 * max(ys)


def write_custom():
    LIB.mkdir(parents=True, exist_ok=True)
    for name, fp in CUSTOM.items():
        (LIB / f"{name}.kicad_mod").write_text(_text(name, fp))


PAD = re.compile(r'\(pad\s+"[^"]*"\s+\w+\s+\w+\s*\(at\s+([-\d.]+)\s+([-\d.]+)[^)]*\)\s*\(size\s+([-\d.]+)\s+([-\d.]+)\)')
FAB = re.compile(r'\(fp_rect\s*\(start\s+([-\d.]+)\s+([-\d.]+)\)\s*\(end\s+([-\d.]+)\s+([-\d.]+)\).*?\(layer\s+"([^"]+)"\)', re.S)


@lru_cache(maxsize=None)
def extent(name: str) -> tuple[float, float]:
    """Width and height of the copper and body of a footprint in the library."""
    if name in CUSTOM:
        return extent_of(CUSTOM[name])
    text = (LIB / f"{name}.kicad_mod").read_text()
    xs, ys = [], []
    for x, y, w, h in PAD.findall(text):
        xs.append(abs(float(x)) + float(w) / 2), ys.append(abs(float(y)) + float(h) / 2)
    for x0, y0, x1, y1, layer in FAB.findall(text):
        if layer == "F.Fab":
            xs += [abs(float(x0)), abs(float(x1))]
            ys += [abs(float(y0)), abs(float(y1))]
    assert xs, name
    return round(2 * max(xs), 3), round(2 * max(ys), 3)


def footprint_of(c) -> str | None:
    """Footprint name for a circuit component."""
    if c.sym.virtual:
        return None
    by_value = {"nRF54L15": "nRF54L15_CSP47", "nPM1304": "nPM1304_CSP35", "W25Q128JW": "W25Q128JW_WLCSP21",
                "T5838": "T5838", "S-82A1A": "DFN-6_1414"}
    if c.value in by_value:
        return by_value[c.value]
    sym, pkg = c.sym.name, c.fields.get("Package", "")
    if sym == "PAD":
        if c.value.startswith("charge"):
            return "Pad_Charge_D1.5"
        return "Pad_Service_D0.8" if c.value in ("SWDIO", "SWDCLK") else "Pad_Test_D1.0"
    if sym == "XTAL":
        return "Crystal_1612_4Pad" if "MHz" in c.value else "Crystal_SMD_2012-2Pin_2.0x1.2mm"
    simple = {"SW": "EVPBB", "LED": "LED_0402_1005Metric", "ANTENNA": "Antenna_1608", "NMOS": "SOT-883",
              "CELL": "Cell_Tabs", "TVS": "D_0201_0603Metric", "D": "D_0201_0603Metric", "FB": "L_0201_0603Metric"}
    if sym in simple:
        return simple[sym]
    if sym == "L":
        return {"0603": "L_0603_1608Metric", "0402": "L_0402_1005Metric"}.get(pkg, "L_0201_0603Metric")
    if sym == "C":
        return "C_0402_1005Metric" if pkg == "0402" else "C_0201_0603Metric"
    return "R_0201_0603Metric"


if __name__ == "__main__":
    write_custom()
    for f in sorted(LIB.glob("*.kicad_mod")):
        print(f"{f.stem:<36} {extent(f.stem)}")
