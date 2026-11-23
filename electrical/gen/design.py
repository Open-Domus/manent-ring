"""The Manent ring circuit as data: parts, values and nets.

Pin tables come from the manufacturers' documents (see parts/pins and docs/design.md).
Anything not confirmed there carries a Note field saying so; those notes end up in the
bill of materials.
"""
from collections import defaultdict

from .emit import Component, Pin, SymDef, two_pin
from .footprints import LIB_NAME, footprint_of

SHEETS = [("power", "Power and charging"), ("mcu_rf", "Microcontroller and radio"),
          ("audio", "Microphone"), ("storage", "Flash memory"), ("ui", "Button, light, pads")]

TYPES = {"pi": "power_in", "po": "power_out", "p": "passive", "i": "input", "o": "output",
         "b": "bidirectional", "nc": "no_connect"}


def ic(name, prefix, spec, width=30.48):
    """spec: lines of 'number name type side'."""
    pins = tuple(Pin(n, nm, TYPES[t], s) for n, nm, t, s in (line.split() for line in spec.strip().splitlines()))
    return SymDef(name, prefix, pins, width)


R, C, L, D, FB = (two_pin(n, p) for n, p in (("R", "R"), ("C", "C"), ("L", "L"), ("D", "D"), ("FB", "FB")))
LED = two_pin("LED", "D")
XTAL = two_pin("XTAL", "Y")
SW = two_pin("SW", "SW")
CELL = two_pin("CELL", "BT")
PAD = SymDef("PAD", "TP", (Pin("1", "~", "passive", "L"),), width=5.08)
ANT = SymDef("ANTENNA", "AE", (Pin("1", "FEED", "passive", "L"),), width=10.16)
FLAG = SymDef("PWR_FLAG", "#FLG", (Pin("1", "pwr", "power_out", "L"),), width=5.08, virtual=True)
NFET = ic("NMOS", "Q", "1 G i L\n2 S p R\n3 D p R", width=10.16)

SOC = ic("nRF54L15-CAAA", "U", """
B7 VDD pi L
G3 VDD pi L
A7 DCC p L
A5 DECD p L
A4 DECA p L
B1 DECRF p L
A6 VSS pi L
G4 VSS pi L
C2 VSS_PA pi L
A1 XC1 p L
A2 XC2 p L
D1 ANT p L
D2 nRESET i L
E3 SWDCLK i L
F2 SWDIO b L
G1 P0.00 b L
F1 P0.01 b L
E2 P0.02 b L
E1 P0.03 b L
D3 P0.04 b L
C5 P1.00/XL1 b L
C6 P1.01/XL2 b L
C7 P1.02 b L
D5 P1.03 b L
D6 P1.04 b R
E6 P1.05 b R
D7 P1.06 b R
E7 P1.07 b R
F7 P1.08 b R
B3 P1.09 b R
C3 P1.10 b R
C4 P1.11 b R
A3 P1.12 b R
B4 P1.13 b R
B5 P1.14 b R
B6 P1.15 b R
G6 P2.00 b R
G7 P2.01 b R
F6 P2.02 b R
E5 P2.03 b R
F5 P2.04 b R
G5 P2.05 b R
F4 P2.06 b R
E4 P2.07 b R
D4 P2.08 b R
F3 P2.09 b R
G2 P2.10 b R
""")

PMIC = ic("nPM1304-CAAA", "U", """
B1 VBUS pi L
B2 VBUS pi L
C3 VBUSOUT p L
B3 CC2 i L
D5 CC1 i L
D1 VBAT p L
D2 VBAT p L
D3 NTC i L
C1 VSYS po L
C2 VSYS p L
C7 PVDD pi L
E4 VDDIO pi L
A6 AVSS pi L
A7 PVSS1 pi L
E7 PVSS2 pi L
E2 VSET1 p L
E1 VSET2 p L
D4 SHPHLD i L
B7 SW1 p R
B6 VOUT1 po R
D7 SW2 p R
C6 VOUT2 p R
B4 LSIN1 pi R
A4 LSOUT1 po R
B5 LSIN2 pi R
A5 LSOUT2 po R
E3 SCL i R
E5 SDA b R
D6 GPIO0 b R
E6 GPIO1 b R
C5 GPIO2 b R
C4 GPIO3 b R
A1 LED0 p R
A2 LED1 p R
A3 LED2 p R
""")

PROT = ic("S-82A1A", "U", "1 VSS pi L\n2 VDD pi L\n3 VINI i L\n4 VM i R\n5 CO o R\n6 DO o R", width=20.32)
MIC = ic("T5838", "MK", "7 VDD pi L\n3 GND pi L\n2 SELECT i L\n6 CLK i R\n1 DATA o R\n5 THSEL i R\n4 WAKE o R", width=20.32)
FLASH = ic("W25Q128JW-WLCSP", "U", "\n".join(
    ["B3 VCC pi L", "E4 GND pi L", "B4 /CS i R", "D3 CLK i R", "E3 DI(IO0) b R", "C4 DO(IO1) b R",
     "D4 /WP(IO2) b R", "C3 /HOLD(IO3) b R"]
    + [f"{b} NC nc L" for b in "A2 A5 A6 B1 B6 C1 C6 D1 D6 E1 E6 F2 F5".split()]), width=25.4)
TVS = two_pin("TVS", "D")

# Which SoC pin does what. The checks in checks.py verify the clock-pin and port rules.
SOC_NETS = {
    "P0.01": "PMIC_INT", "P0.02": "I2C_SDA", "P0.03": "I2C_SCL", "P0.04": "LED_AUX",
    "P1.00/XL1": "XL1", "P1.01/XL2": "XL2",
    "P1.04": "PDM_CLK", "P1.05": "PDM_DIN", "P1.06": "MIC_THSEL", "P1.07": "MIC_WAKE",
    "P1.13": "MIC_EN", "P1.14": "UART_TX", "P1.15": "UART_RX",
    "P2.01": "SPI_SCK", "P2.02": "SPI_SDO", "P2.04": "SPI_SDI", "P2.05": "FLASH_CS",
}

UNVERIFIED_CAPS = "Value from Nordic's reference list; which net each capacitor sits on is not confirmed"


def build() -> list[Component]:
    comps: list[Component] = []
    count = defaultdict(int)

    def add(sym, value, sheet, nets, mpn="", mfr="", package="", note="", dnp=False):
        count[sym.prefix] += 1
        if isinstance(nets, (list, tuple)):
            nets = {p.number: n for p, n in zip(sym.pins, nets)}
        fields = {"MPN": mpn, "Manufacturer": mfr, "Package": package, "Note": note}
        comps.append(Component(f"{sym.prefix}{count[sym.prefix]}", sym, value, sheet, nets,
                               {k: v for k, v in fields.items() if v}, dnp))

    def by_name(sym, mapping):
        """Nets keyed by pin name; pins not named get a no-connect."""
        return {p.number: mapping.get(p.name) for p in sym.pins}

    cap = lambda v, net, sheet, pkg="0201", note="", **kw: add(C, v, sheet, (net, "GND"), package=pkg, note=note, **kw)
    res = lambda v, a, b, sheet, note="", **kw: add(R, v, sheet, (a, b), package="0201", note=note, **kw)

    # ---- power -------------------------------------------------------------------
    add(PMIC, "nPM1304", "power", by_name(PMIC, {
        "VBUS": "VBUS", "VBUSOUT": "VBUSOUT", "CC1": "GND", "CC2": "GND", "VBAT": "VBAT", "NTC": "NTC",
        "VSYS": "VSYS", "PVDD": "VSYS", "VDDIO": "V1V8", "AVSS": "GND", "PVSS1": "GND", "PVSS2": "GND",
        "VSET1": "VSET1", "VSET2": "GND", "SHPHLD": "BTN_N", "SW1": "SW1", "VOUT1": "V1V8",
        "VOUT2": "GND", "LSIN1": "V1V8", "LSOUT1": "VMIC", "LSIN2": "V1V8", "LSOUT2": "VFLASH",
        "SCL": "I2C_SCL", "SDA": "I2C_SDA", "GPIO0": "PMIC_INT", "GPIO1": "MIC_EN",
    }), mpn="nPM1304-CAAA-R", mfr="Nordic Semiconductor", package="WLCSP-35",
        note="BUCK2 unused: VSET2 grounded as documented; SW2 open and VOUT2 grounded are not confirmed. "
             "LED0-2, GPIO2-3 left open: not confirmed")
    res("10k NTC", "NTC", "GND", "power", note="Thermistor, to sit against the cell: stops charging when hot or cold")
    add(L, "2.2uH", "power", ("SW1", "V1V8"), mpn="to choose", package="0603",
        note="DCR <= 0.4 ohm, Isat > 350 mA; part and height to choose")
    res("47k", "VSET1", "GND", "power", note="Sets BUCK1 to 1.8 V at power-on")
    cap("1uF 25V", "VBUS", "power", pkg="0402", note=UNVERIFIED_CAPS)
    cap("1uF", "VBUSOUT", "power", note=UNVERIFIED_CAPS)
    cap("10uF", "VBAT", "power", pkg="0402", note=UNVERIFIED_CAPS)
    cap("10uF", "VSYS", "power", pkg="0402", note=UNVERIFIED_CAPS)
    cap("10uF", "V1V8", "power", pkg="0402", note="Buck output: at least 4 uF effective")
    cap("100nF", "V1V8", "power", note="VDDIO")
    cap("1uF", "VMIC", "power", note="Load switch output; value to confirm")
    res("470k", "VMIC", "GND", "power", note="Empties the rail when the switch opens, so the light goes out with the microphone")
    cap("1uF", "VFLASH", "power", note="Load switch output; value to confirm")
    res("10k", "I2C_SCL", "V1V8", "power")
    res("10k", "I2C_SDA", "V1V8", "power")
    add(TVS, "5.5V unidirectional", "power", ("VBUS", "GND"), mpn="to choose", package="0201",
        note="Pin 1 is the cathode. Unidirectional, so that a negative strike is clamped near -0.7 V")
    add(PAD, "charge +", "power", ("VBUS",), note="Centre pad on the inner surface")
    add(PAD, "charge -", "power", ("GND",), note="Outer pad; two of them make the dock reversible")
    add(PAD, "charge -", "power", ("GND",))
    add(FLAG, "PWR_FLAG", "power", ("VBUS",))
    add(FLAG, "PWR_FLAG", "power", ("GND",))
    add(FLAG, "PWR_FLAG", "power", ("CELL_P",))
    add(FLAG, "PWR_FLAG", "power", ("CELL_N",))
    # Cell and protection (only if the cell ships without its own protection board)
    add(CELL, "curved LiPo 3.8 V", "power", ("VBAT", "CELL_N"), mpn="GRP1707xx / GRP160626", mfr="Grepow",
        note="Capacity depends on ring size; see docs/space-budget.md")
    add(FLAG, "PWR_FLAG", "power", ("VBAT",))
    res("330", "VBAT", "CELL_P", "power", note="Protector supply filter")
    cap("1uF", "CELL_P", "power", note="With the 330 ohm: at least 100 uF x ohm, as the protector asks")
    comps[-1].nets = {"1": "CELL_P", "2": "CELL_N"}
    add(PROT, "S-82A1A", "power", by_name(PROT, {"VSS": "CELL_N", "VDD": "CELL_P", "VINI": "SENSE",
                                                 "VM": "VM", "CO": "PROT_CO", "DO": "PROT_DO"}),
        mpn="S-82A1AAG-A6T5S (variant to confirm)", mfr="ABLIC", package="DFN-6 1.4x1.4",
        note="Fit only if the cell has no protection of its own. This variant trips at 4.23 V: right for a "
             "4.20 V cell with little margin, wrong for a 4.35 V one. Choose with the cell")
    res("0.5", "CELL_N", "SENSE", "power",
        note="Overcurrent sense: trips at 100 mA out and 60 mA in (50 mV and 30 mV thresholds); to check against peaks")
    res("470", "VM", "GND", "power")
    add(NFET, "N-MOSFET, low resistance", "power", {"1": "PROT_DO", "2": "SENSE", "3": "FET_MID"}, mpn="to choose",
        note="Discharge FET; carries the cell current")
    add(NFET, "N-MOSFET, low resistance", "power", {"1": "PROT_CO", "2": "GND", "3": "FET_MID"}, mpn="to choose",
        note="Charge FET; carries the cell current")

    # ---- microcontroller and radio (Nordic CAAA reference circuit 0.7, DC/DC, NFC off) --
    add(SOC, "nRF54L15", "mcu_rf", by_name(SOC, {
        "VDD": "V1V8", "DCC": "DCC", "DECD": "DECD", "DECA": "DECA", "DECRF": "DECRF",
        "VSS": "GND", "VSS_PA": "GND", "XC1": "XC1", "XC2": "XC2", "ANT": "ANT",
        "nRESET": "NRESET", "SWDCLK": "SWDCLK", "SWDIO": "SWDIO", **SOC_NETS,
    }), mpn="nRF54L15-CAAA-R", mfr="Nordic Semiconductor", package="WLCSP-47, 0.3 mm pitch",
        note="Light-sensitive package: the resin around it must be opaque")
    cap("10uF", "V1V8", "mcu_rf", pkg="0402")
    cap("100nF", "V1V8", "mcu_rf")
    cap("100nF", "V1V8", "mcu_rf")
    add(L, "4.7uH", "mcu_rf", ("DCC", "DECD"), mpn="PLEA67BCA4R7M-1PT00", mfr="TDK", package="0402")
    cap("2.2uF", "DECD", "mcu_rf", mpn="GRM033R61A225KE47", mfr="Murata")
    add(FB, "120R@100MHz", "mcu_rf", ("DECD", "DECA"), mpn="BLM03AG121SN1D", mfr="Murata", package="0201")
    cap("2.2uF", "DECA", "mcu_rf", mpn="GRM033R61A225KE47", mfr="Murata")
    cap("10nF", "DECA", "mcu_rf", dnp=True, note="Not fitted in Nordic's reference")
    add(FB, "120R@100MHz", "mcu_rf", ("DECA", "DECRF"), mpn="BLM03AG121SN1D", mfr="Murata", package="0201")
    cap("2.2uF", "DECRF", "mcu_rf", mpn="GRM033R61A225KE47", mfr="Murata")
    cap("3.9pF", "DECRF", "mcu_rf", dnp=True, note="Not fitted in Nordic's reference")
    add(XTAL, "32MHz 8pF", "mcu_rf", ("XC1", "XC2"), mpn="CX1612DB32000D0WZRC3", mfr="Kyocera", package="1612",
        note="Load capacitors are inside the chip")
    add(XTAL, "32.768kHz 9pF", "mcu_rf", ("XL1", "XL2"), mpn="9HT11-32.768KDZC-T", mfr="TXC", package="2012",
        dnp=True, note="Optional: start on the internal RC oscillator")
    add(L, "4.7nH", "mcu_rf", ("ANT", "RF_A"), mpn="LQP03HQ4N7H02", mfr="Murata", package="0201")
    cap("1.2pF", "RF_A", "mcu_rf", mpn="GJM0335C1H1R2WB01D", mfr="Murata")
    add(L, "4.7nH", "mcu_rf", ("RF_A", "RF_B"), mpn="LQP03HQ4N7H02", mfr="Murata", package="0201")
    cap("1.2pF", "RF_B", "mcu_rf", mpn="GJM0335C1H1R2WB01D", mfr="Murata")
    add(L, "2.0nH", "mcu_rf", ("RF_B", "RF_50"), mpn="LQP03HQ2N0B02", mfr="Murata", package="0201")
    res("0", "RF_50", "ANT_FEED", "mcu_rf", note="Antenna tuning, series: value from measurement on a potted ring")
    cap("tune", "RF_50", "mcu_rf", dnp=True, note="Antenna tuning, shunt")
    cap("tune", "ANT_FEED", "mcu_rf", dnp=True, note="Antenna tuning, shunt")
    add(ANT, "2.4 GHz", "mcu_rf", ("ANT_FEED",), mpn="to choose",
        note="Chip antenna or printed trace at the band edge; decided with the first radio measurements")

    # ---- microphone ----------------------------------------------------------------
    add(MIC, "T5838", "audio", by_name(MIC, {"VDD": "VMIC", "GND": "GND", "SELECT": "GND", "CLK": "PDM_CLK",
                                             "DATA": "PDM_DIN", "THSEL": "MIC_THSEL", "WAKE": "MIC_WAKE"}),
        mpn="MMICT5838-00-012", mfr="TDK InvenSense", package="3.5x2.65x0.98 bottom port",
        note="No pull resistor on DATA. Board hole 0.5-1.0 mm under the port")
    cap("100nF", "VMIC", "audio", note="X7R, next to pin 7")

    # ---- flash ---------------------------------------------------------------------
    add(FLASH, "W25Q128JW", "storage", by_name(FLASH, {
        "VCC": "VFLASH", "GND": "GND", "/CS": "FLASH_CS", "CLK": "SPI_SCK", "DI(IO0)": "SPI_SDO",
        "DO(IO1)": "SPI_SDI", "/WP(IO2)": "FLASH_IO2", "/HOLD(IO3)": "FLASH_IO3"}),
        mpn="W25Q128JWYIQ (or thin W25Q128JWKIQ)", mfr="Winbond", package="WLCSP-21, 0.5 mm pitch",
        note="Special-order package; body size not published, ask Winbond")
    cap("100nF", "VFLASH", "storage")
    res("100k", "FLASH_CS", "VFLASH", "storage", note="Keeps the chip deselected while the rail rises")
    res("100k", "FLASH_IO2", "VFLASH", "storage", note="Termination in single-bit SPI not stated in the datasheet")
    res("100k", "FLASH_IO3", "VFLASH", "storage", note="Termination in single-bit SPI not stated in the datasheet")

    # ---- button, light, pads -----------------------------------------------------------
    add(SW, "tactile", "ui", ("BTN_N", "GND"), mpn="EVPBB2A9B000", mfr="Panasonic", package="2.6x1.6x0.53",
        note="1.6 N; pulled up inside the PMIC (SHPHLD). The SoC learns of presses from the PMIC interrupt")
    add(LED, "red", "ui", ("LED_K", "VSYS"), mpn="SML-P11VT", mfr="Rohm", package="1.0x0.6x0.2",
        note="Pin 1 is the cathode. For the wearer only: about 0.1 mA")
    res("22k", "LED_K", "LED_SW", "ui", note="About 0.06-0.11 mA over the cell voltage; adjust after a look through the resin")
    add(NFET, "N-MOSFET, small signal", "ui", {"1": "VMIC", "2": "GND", "3": "LED_SW"}, mpn="to choose",
        note="Gate is the microphone rail: the light is on whenever the microphone has power. Vgs(th) under 1 V")
    add(NFET, "N-MOSFET, small signal", "ui", {"1": "LED_AUX", "2": "GND", "3": "LED_SW"}, mpn="to choose",
        note="Lets firmware blink the light for errors and charging")
    res("100k", "LED_AUX", "GND", "ui", note="Light off while the SoC is in reset")
    for label, net in (("SWDIO", "SWDIO"), ("SWDCLK", "SWDCLK")):
        res("100", net, net + "_PAD", "ui", note="Between the chip and a pad that touches the skin")
        add(PAD, label, "ui", (net + "_PAD",), note="Service pad on the inner surface: reachable after potting")
    for label, net in (("nRESET", "NRESET"), ("UART TX", "UART_TX"), ("UART RX", "UART_RX"), ("1V8", "V1V8"),
                       ("GND", "GND"), ("VBAT", "VBAT"), ("VBUS", "VBUS")):
        add(PAD, label, "ui", (net,), note="Test tail, cut off before potting")
    for c in comps:
        fp = footprint_of(c)
        if fp:
            c.fields["Footprint"] = f"{LIB_NAME}:{fp}"
    return comps


def netlist(comps=None) -> dict[str, set[tuple[str, str]]]:
    nets = defaultdict(set)
    for c in comps or build():
        for pin, net in c.nets.items():
            if net is not None:
                nets[net].add((c.ref, pin))
    return dict(nets)
