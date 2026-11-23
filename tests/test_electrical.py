from pathlib import Path

import pytest

from gen import checks
from gen.design import build, netlist

NETLIST = Path(__file__).resolve().parents[1] / "electrical" / "out" / "netlist.xml"


def test_circuit_rules_hold():
    assert checks.lint() == []


def test_kicad_reads_the_same_nets_we_wrote():
    if not NETLIST.exists():
        pytest.skip("run `make schematic` first")
    assert checks.compare(NETLIST) == []
    assert len(checks.kicad_netlist(NETLIST)) == len(netlist()) > 40


def test_light_follows_the_microphone_rail():
    # The recording light must not depend on firmware: its switch is gated by VMIC itself.
    comps = build()
    gate = [c for c in comps if c.sym.name == "NMOS" and c.nets["1"] == "VMIC"]
    assert len(gate) == 1 and gate[0].nets["3"] == "LED_SW"
    mic = next(c for c in comps if c.value == "T5838")
    assert "VMIC" in mic.nets.values()


def test_no_vibration_motor():
    assert not any("haptic" in c.value.lower() or "motor" in c.value.lower() for c in build())
