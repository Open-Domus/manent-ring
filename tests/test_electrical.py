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


def test_board_is_routed_without_rule_violations():
    import json
    drc = NETLIST.with_name("drc.json")
    if not drc.exists():
        pytest.skip("run `make board` first")
    report = json.loads(drc.read_text())
    assert report["violations"] == []
    assert report["schematic_parity"] == []       # same parts, footprints and nets as the schematic
    assert report["unconnected_items"] == []      # every connection is made


# ---- claims about the routing that KiCad's rule check does not cover -----------------

OUT = NETLIST.parent


@pytest.fixture(scope="module")
def routed():
    import json
    return json.loads((OUT / "routes.json").read_text()), json.loads((OUT / "board.json").read_text())


def _segments(routes):
    for t in routes["tracks"]:
        for a, b in zip(t["pts"], t["pts"][1:]):
            yield t["net"], t["layer"], a, b


def test_every_connection_was_routed(routed):
    assert routed[0]["failed"] == []


def test_only_the_two_flex_layers_cross_the_bends_and_no_via_is_near_them(routed):
    routes, board = routed
    flex = {routes["layers"] // 2 - 1, routes["layers"] // 2}
    bends = [(z["x0"], z["x1"]) for z in board["zones"] if z["kind"] == "bend"]
    assert len(bends) == 7
    for net, layer, a, b in _segments(routes):
        lo, hi = sorted((a[0], b[0]))
        if layer not in flex:
            assert not any(lo < x1 and hi > x0 for x0, x1 in bends), (net, layer, a, b)
    for v in routes["vias"]:
        assert not any(x0 - 0.29 < v["x"] < x1 + 0.29 for x0, x1 in bends), v


def test_cutting_the_test_tail_cuts_nothing_else(routed):
    routes, board = routed
    cut = board["tail_cut"][2]
    tail_nets = {"NRESET", "UART_TX", "UART_RX", "V1V8", "GND", "VBAT", "VBUS"}
    # The tail is rigid, so a stub may change layer on it; what matters is what the cut severs.
    assert {v["net"] for v in routes["vias"] if v["y"] > cut} <= tail_nets
    crossings = {}
    for net, layer, a, b in _segments(routes):
        if (a[1] > cut) != (b[1] > cut):
            crossings[net] = crossings.get(net, 0) + 1
    # one stub per test pad and nothing else: no net runs through the tail and back
    assert crossings == {net: 1 for net in tail_nets}
    assert routes["plane"]["net"] == "GND"


def test_nothing_runs_under_the_switch(routed):
    routes, board = routed
    sw = next(p for p in board["parts"] if p["footprint"] == "EVPBB")
    hx, hy = (0.8, 1.0) if sw["rot"] else (1.0, 0.8)
    layer = 0 if sw["side"] == "F" else routes["layers"] - 1
    inside = lambda x, y: abs(x - sw["x"]) < hx - 0.05 and abs(y - sw["y"]) < hy - 0.05
    for net, l, a, b in _segments(routes):
        if l == layer:
            assert not inside(*a) and not inside(*b), (net, a, b)
    for v in routes["vias"]:
        if v["l1"] <= layer <= v["l2"]:
            assert not inside(v["x"], v["y"]), v


def test_vias_on_grid_packages_sit_on_pad_centres(routed):
    routes, board = routed
    from gen.footprints import CUSTOM
    for part in board["parts"]:
        fp = CUSTOM.get(part["footprint"])
        if part["footprint"] not in ("nRF54L15_CSP47", "nPM1304_CSP35", "W25Q128JW_WLCSP21"):
            continue
        layer = 0 if part["side"] == "F" else routes["layers"] - 1
        sx = -1 if part["side"] == "B" else 1            # bottom parts are mirrored left to right
        for _, _, px, py, d, _ in fp["pads"]:
            if part["rot"]:
                px, py = py, -px
            cx, cy = part["x"] + sx * px, part["y"] + py
            for v in routes["vias"]:
                if v["l1"] <= layer <= v["l2"]:
                    dist = ((v["x"] - cx) ** 2 + (v["y"] - cy) ** 2) ** 0.5
                    assert dist < 0.005 or dist > d / 2 + 0.1 - 0.005, (part["ref"], v, dist)


ROOT = Path(__file__).resolve().parents[1]


def test_quote_request_quotes_the_board_as_it_is():
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    from board_facts import facts
    f, text = facts(), (ROOT / "quote" / "request.md").read_text()
    strip_l, strip_w = f["strip"].split(" x ")
    for claim in (f"strip {float(strip_l):.1f} x {strip_w} mm", f"{f['vias']} in all",
                  f"{f['vias, adjacent layers']} between adjacent layers", f"{f['vias, stacked']} stacked",
                  f"{f['vias, through all layers']} through all six", f"| Parts | {f['parts to place']} to place"):
        assert claim in text, claim
    assert f["bends"] == 7 and "seven bends" in text
    assert f["rigid areas"] == 8 and "eight along the strip" in text
