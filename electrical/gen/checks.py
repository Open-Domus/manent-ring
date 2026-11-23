"""Checks on the circuit that do not need KiCad, and the comparison with what KiCad read."""
import csv
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from .design import SOC_NETS, build, netlist

ROOT = Path(__file__).resolve().parents[2]
RAILS = {"GND", "V1V8", "VSYS", "VBAT", "VBUS", "VMIC", "VFLASH"}
CLOCK_NETS = {"PDM_CLK", "SPI_SCK", "I2C_SCL"}
SAME_PORT = [("PDM_CLK", "PDM_DIN"), ("SPI_SCK", "SPI_SDO", "SPI_SDI", "FLASH_CS"), ("I2C_SCL", "I2C_SDA")]
WAKE_NETS = {"BTN_WAKE", "MIC_WAKE", "PMIC_INT"}
DECOUPLED = {"U": ("power_in",), "MK": ("power_in",)}


def kicad_netlist(path: Path) -> dict[str, set[tuple[str, str]]]:
    nets = {}
    for net in ET.parse(path).getroot().iter("net"):
        name = net.get("name").lstrip("/")
        if not name.startswith("unconnected-"):
            nets[name] = {(n.get("ref"), n.get("pin")) for n in net.iter("node")}
    return nets


def compare(path: Path) -> list[str]:
    ours, theirs = netlist(), kicad_netlist(path)
    ours = {k: {(r, p) for r, p in v if not r.startswith("#")} for k, v in ours.items()}
    theirs = {k: {(r, p) for r, p in v if not r.startswith("#")} for k, v in theirs.items()}
    out = [f"net {n} missing in KiCad" for n in ours.keys() - theirs.keys()]
    out += [f"net {n} only in KiCad" for n in theirs.keys() - ours.keys()]
    out += [f"net {n} differs: {sorted(ours[n] ^ theirs[n])}" for n in ours.keys() & theirs.keys() if ours[n] != theirs[n]]
    return out


def lint() -> list[str]:
    comps = build()
    nets = netlist(comps)
    out = [f"net {n} has a single pin" for n, pins in nets.items() if len(pins) < 2]
    refs = [c.ref for c in comps]
    out += [f"duplicate reference {r}" for r in set(refs) if refs.count(r) > 1]

    # Every supply pin of an integrated circuit sits on a net with a capacitor to ground.
    with_cap = {c.nets["1"] for c in comps if c.sym.name == "C" and c.nets["2"] in ("GND", "CELL_N") and not c.dnp}
    for c in comps:
        if c.sym.prefix in ("U", "MK"):
            for p in c.sym.pins:
                net = c.nets.get(p.number)
                if p.etype == "power_in" and net not in ("GND", "CELL_N") and net not in with_cap:
                    out.append(f"{c.ref} pin {p.name} ({net}) has no decoupling capacitor")

    # Microcontroller pin rules, from parts/pins/nrf54l15_csp47.yaml.
    pins = yaml.safe_load((ROOT / "parts" / "pins" / "nrf54l15_csp47.yaml").read_text())["pins"]
    info = {v["name"]: v for v in pins.values()}
    where = {net: pin.split("/")[0] for pin, net in SOC_NETS.items()}
    for net in CLOCK_NETS:
        if not info[where[net]].get("ck"):
            out.append(f"{net} is on {where[net]}, which is not a clock pin")
    for group in SAME_PORT:
        if len({where[n][:2] for n in group}) != 1:
            out.append(f"{group} are not all on one port")
    if where["PDM_CLK"][:2] != "P1":
        out.append("PDM must be on port 1")
    if (where["SPI_SCK"], where["SPI_SDO"], where["SPI_SDI"], where["FLASH_CS"]) != ("P2.01", "P2.02", "P2.04", "P2.05"):
        out.append("fast SPI is not on its dedicated pins")
    out += [f"{n} is on {where[n]}: port 2 cannot wake the chip" for n in WAKE_NETS if where[n].startswith("P2")]
    soc = next(c for c in comps if c.value == "nRF54L15")
    sym_pins = {p.number: p.name.split("/")[0] for p in soc.sym.pins}
    out += [f"SoC symbol pin {n} is {sym_pins.get(n)}, the pin table says {v['name']}"
            for n, v in pins.items() if sym_pins.get(n) != v["name"]]

    # Everything to buy names a part or says it is still to choose.
    out += [f"{c.ref} has no package" for c in comps if not c.sym.virtual and c.sym.name != "PAD"
            and not c.fields.get("Package") and not c.fields.get("MPN")]
    return out


def write_bom(path: Path):
    rows = {}
    for c in build():
        if c.sym.virtual or c.sym.name == "PAD":
            continue
        key = (c.sym.name, c.value, c.fields.get("MPN", ""), c.fields.get("Package", ""), c.dnp)
        row = rows.setdefault(key, {"refs": [], "notes": []})
        row["refs"].append(c.ref)
        if c.fields.get("Note") and c.fields["Note"] not in row["notes"]:
            row["notes"].append(c.fields["Note"])
        row["mfr"] = c.fields.get("Manufacturer", "")
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["References", "Quantity", "Value", "Manufacturer", "Part number", "Package", "Fitted", "Notes"])
        for (sym, value, mpn, pkg, dnp), row in rows.items():
            w.writerow([" ".join(row["refs"]), len(row["refs"]), value, row["mfr"], mpn, pkg,
                        "no" if dnp else "yes", " | ".join(row["notes"])])
    return sum(len(r["refs"]) for r in rows.values()), len(rows)


if __name__ == "__main__":
    problems = lint()
    xml = ROOT / "electrical" / "out" / "netlist.xml"
    if xml.exists():
        problems += compare(xml)
    else:
        print("no KiCad netlist yet: run `make schematic`")
    n, lines = write_bom(ROOT / "electrical" / "out" / "bom.csv")
    print(f"bill of materials: {n} parts on {lines} lines")
    print("\n".join(problems) if problems else "circuit checks: no problems")
    raise SystemExit(1 if problems else 0)
