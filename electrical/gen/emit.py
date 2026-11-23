"""Write KiCad schematic files from the design in design.py.

Every symbol comes from a library generated here (no dependence on the stock KiCad
libraries). Every pin carries a global label naming its net, so connectivity never
depends on drawn wires; unconnected pins get an explicit no-connect mark.
"""
import uuid
from dataclasses import dataclass, field
from pathlib import Path

GRID = 2.54
NS = uuid.UUID("6d616e65-6e74-4d61-8e65-6e7472696e67")   # fixed, so files diff cleanly
PROJECT = "manent"
VERSION = 20250114
FONT = "(effects (font (size 1.27 1.27)))"


def uid(*key) -> str:
    return str(uuid.uuid5(NS, "/".join(str(k) for k in key)))


def q(text) -> str:
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


@dataclass(frozen=True)
class Pin:
    number: str
    name: str
    etype: str = "passive"      # KiCad electrical type
    side: str = "L"             # "L" or "R"


@dataclass(frozen=True)
class SymDef:
    name: str
    prefix: str
    pins: tuple[Pin, ...]
    width: float = 20.32
    virtual: bool = False       # drawn, but not a part to buy or place

    def layout(self) -> dict[str, tuple[float, float, int]]:
        """Pin number -> (x, y, angle) of its connection point, library coordinates."""
        out = {}
        for side, x, ang in (("L", -self.width / 2 - GRID, 0), ("R", self.width / 2 + GRID, 180)):
            pins = [p for p in self.pins if p.side == side]
            for i, p in enumerate(pins):
                out[p.number] = (x, (len(pins) - 1) / 2 * GRID - i * GRID, ang)
        return out

    @property
    def height(self) -> float:
        n = max(sum(p.side == s for p in self.pins) for s in "LR")
        return (n + 1) * GRID


@dataclass
class Component:
    ref: str
    sym: SymDef
    value: str
    sheet: str
    nets: dict[str, str | None]              # pin number -> net name, None = no connect
    fields: dict[str, str] = field(default_factory=dict)
    dnp: bool = False


def two_pin(name: str, prefix: str) -> SymDef:
    return SymDef(name, prefix, (Pin("1", "~", "passive", "L"), Pin("2", "~", "passive", "R")), width=5.08)


def _lib_symbol(sd: SymDef, lib: str = PROJECT + ":") -> str:
    h, w = sd.height, sd.width
    hide_names = "(pin_names (offset 0.508) (hide yes))" if len(sd.pins) == 2 else "(pin_names (offset 0.508))"
    props = "".join(
        f'\n\t\t\t(property {q(k)} {q(v)} (at 0 {y:.2f} 0) (effects (font (size 1.27 1.27)){hide}))'
        for k, v, y, hide in (("Reference", sd.prefix, h / 2 + 1.27, ""), ("Value", sd.name, -h / 2 - 1.27, ""),
                              ("Footprint", "", 0, " (hide yes)"), ("Datasheet", "", 0, " (hide yes)")))
    pins = "".join(
        f'\n\t\t\t\t(pin {p.etype} line (at {x:.2f} {y:.2f} {a}) (length {GRID}) '
        f'(name {q(p.name)} {FONT}) (number {q(p.number)} {FONT}))'
        for p in sd.pins for x, y, a in [sd.layout()[p.number]])
    return (f'\n\t\t(symbol {q(lib + sd.name)} {hide_names} (exclude_from_sim no) (in_bom {"no" if sd.virtual else "yes"}) (on_board {"no" if sd.virtual else "yes"})'
            f'{props}'
            f'\n\t\t\t(symbol {q(sd.name + "_0_1")}\n\t\t\t\t(rectangle (start {-w / 2:.2f} {h / 2:.2f}) (end {w / 2:.2f} {-h / 2:.2f}) '
            f'(stroke (width 0.254) (type default)) (fill (type background))))'
            f'\n\t\t\t(symbol {q(sd.name + "_1_1")}{pins})'
            f'\n\t\t\t(embedded_fonts no))')


def library(symdefs) -> str:
    body = "".join(_lib_symbol(sd, "").replace("\n\t\t", "\n\t") for sd in symdefs)
    return (f'(kicad_symbol_lib (version {VERSION}) (generator "manent_gen") (generator_version "1")'
            f'{body}\n)\n')


def _place(components) -> dict[str, tuple[float, float]]:
    """Columns of parts: integrated circuits first, then two-pin parts in a tight grid."""
    pos, x, y = {}, 75.0, 40.0
    big = [c for c in components if len(c.sym.pins) > 2]
    small = [c for c in components if len(c.sym.pins) <= 2]
    for c in big:
        h = c.sym.height + 4 * GRID
        if y + h > 270:
            x, y = x + 110.0, 40.0
        pos[c.ref] = (round(x / GRID) * GRID, round((y + h / 2) / GRID) * GRID)
        y += h
    x, y = x + 100.0, 40.0
    for c in small:
        if y > 265:
            x, y = x + 62.0, 40.0
        pos[c.ref] = (round(x / GRID) * GRID, round(y / GRID) * GRID)
        y += 4 * GRID
    return pos


def sheet_file(name: str, components, root_uuid: str, title: str, paper: str = "A3") -> str:
    sheet_uuid = uid("sheet", name)
    path = f"/{root_uuid}/{sheet_uuid}"
    symdefs = {c.sym.name: c.sym for c in components}
    out = [f'(kicad_sch (version {VERSION}) (generator "manent_gen") (generator_version "1")',
           f'\t(uuid {q(uid("file", name))})', f'\t(paper {q(paper)})',
           f'\t(title_block (title {q(title)}) (company "Manent"))',
           '\t(lib_symbols' + "".join(_lib_symbol(sd) for sd in symdefs.values()) + '\n\t)']
    pos = _place(components)
    for c in components:
        cx, cy = pos[c.ref]
        lay = c.sym.layout()
        h = c.sym.height
        props = [("Reference", c.ref, cx, cy - h / 2 - 1.27, False), ("Value", c.value, cx, cy + h / 2 + 1.27, False),
                 ("Footprint", c.fields.get("Footprint", ""), cx, cy, True),
                 ("Datasheet", c.fields.get("Datasheet", ""), cx, cy, True)]
        props += [(k, v, cx, cy, True) for k, v in c.fields.items() if k not in ("Footprint", "Datasheet")]
        ptxt = "".join(
            f'\n\t\t(property {q(k)} {q(v)} (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)){" (hide yes)" if hide else ""}))'
            for k, v, x, y, hide in props)
        pintxt = "".join(f'\n\t\t(pin {q(p.number)} (uuid {q(uid(name, c.ref, "pin", p.number))}))' for p in c.sym.pins)
        out.append(
            f'\t(symbol (lib_id {q(PROJECT + ":" + c.sym.name)}) (at {cx:.2f} {cy:.2f} 0) (unit 1)'
            f' (exclude_from_sim no) (in_bom {"no" if c.sym.virtual else "yes"}) (on_board {"no" if c.sym.virtual else "yes"}) (dnp {"yes" if c.dnp else "no"})'
            f' (uuid {q(uid(name, c.ref))}){ptxt}{pintxt}'
            f'\n\t\t(instances (project {q(PROJECT)} (path {q(path)} (reference {q(c.ref)}) (unit 1))))\n\t)')
        for p in c.sym.pins:
            px, py, ang = lay[p.number]
            x, y = cx + px, cy - py
            net = c.nets.get(p.number)
            if net is None:
                out.append(f'\t(no_connect (at {x:.2f} {y:.2f}) (uuid {q(uid(name, c.ref, "nc", p.number))}))')
            else:
                rot, just = (180, "right") if ang == 0 else (0, "left")
                out.append(
                    f'\t(global_label {q(net)} (shape passive) (at {x:.2f} {y:.2f} {rot})'
                    f' (effects (font (size 1.27 1.27)) (justify {just}))'
                    f' (uuid {q(uid(name, c.ref, "label", p.number))})'
                    f'\n\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n\t)')
    out.append(f'\t(sheet_instances (path "/" (page "1")))\n\t(embedded_fonts no)\n)\n')
    return "\n".join(out)


def root_file(sheets: list[tuple[str, str]], root_uuid: str) -> str:
    out = [f'(kicad_sch (version {VERSION}) (generator "manent_gen") (generator_version "1")',
           f'\t(uuid {q(root_uuid)})', '\t(paper "A4")',
           '\t(title_block (title "Manent ring") (company "Manent"))', '\t(lib_symbols)']
    for i, (name, title) in enumerate(sheets):
        x, y = 30 + (i % 3) * 80, 40 + (i // 3) * 60
        out.append(
            f'\t(sheet (at {x} {y}) (size 60 30) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)'
            f'\n\t\t(stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0)) (uuid {q(uid("sheet", name))})'
            f'\n\t\t(property "Sheetname" {q(title)} (at {x} {y - 0.7} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))'
            f'\n\t\t(property "Sheetfile" {q(name + ".kicad_sch")} (at {x} {y + 30.6} 0) (effects (font (size 1.27 1.27)) (justify left top)))'
            f'\n\t\t(instances (project {q(PROJECT)} (path {q("/" + root_uuid)} (page {q(i + 2)}))))\n\t)')
    out.append('\t(sheet_instances (path "/" (page "1")))\n\t(embedded_fonts no)\n)\n')
    return "\n".join(out)


def write_project(outdir: Path, components: list[Component], sheets: list[tuple[str, str]]):
    outdir.mkdir(parents=True, exist_ok=True)
    root_uuid = uid("root")
    (outdir / f"{PROJECT}.kicad_sch").write_text(root_file(sheets, root_uuid))
    for name, title in sheets:
        (outdir / f"{name}.kicad_sch").write_text(
            sheet_file(name, [c for c in components if c.sheet == name], root_uuid, title))
    symdefs = {c.sym.name: c.sym for c in components}
    (outdir / f"{PROJECT}.kicad_sym").write_text(library(symdefs.values()))
    (outdir / "sym-lib-table").write_text(
        f'(sym_lib_table\n\t(version 7)\n\t(lib (name {q(PROJECT)}) (type "KiCad") '
        f'(uri "${{KIPRJMOD}}/{PROJECT}.kicad_sym") (options "") (descr "Generated by electrical/gen"))\n)\n')
    (outdir / "fp-lib-table").write_text(
        f'(fp_lib_table\n\t(version 7)\n\t(lib (name {q(PROJECT)}) (type "KiCad") '
        f'(uri "${{KIPRJMOD}}/{PROJECT}.pretty") (options "") (descr "Project footprints"))\n)\n')
    pro = outdir / f"{PROJECT}.kicad_pro"
    if not pro.exists():
        pro.write_text('{\n  "meta": {"filename": "manent.kicad_pro", "version": 3}\n}\n')
