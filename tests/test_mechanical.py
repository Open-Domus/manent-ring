import pytest

from manent_mech import stack as S
from manent_mech.checks import envelope_report, size_sweep
from manent_mech.params import SITE, WIDE
from manent_mech.profile import cavity_height


def test_site_envelope_reproduces_the_render_numbers():
    # manent-site/assets/ring.js: R = 10.6, HX = 1.2, HY = 3.7, CROWN = 0.28, RTOP = 12.08
    assert SITE.band_width == pytest.approx(7.4)
    assert SITE.wall_edge == pytest.approx(2.4)
    assert SITE.wall_centre == pytest.approx(2.96)
    assert SITE.outer_diameter / 2 == pytest.approx(12.08)
    assert cavity_height(SITE, 6.0) == pytest.approx(1.80, abs=0.01)


def test_both_envelopes_sit_on_the_same_finger():
    assert WIDE.inner_diameter_min == pytest.approx(SITE.inner_diameter_min)


@pytest.fixture(scope="module")
def reports():
    return {k: envelope_report(k) for k in ("A", "B")}


@pytest.mark.parametrize("key", ["A", "B"])
def test_every_island_fits_radially(reports, key):
    bad = [i for i in reports[key]["islands"] if not i["ok"]]
    assert not bad, bad


def test_wide_envelope_fits_a_catalogue_cell(reports):
    assert reports["B"]["ok"], reports["B"]


def test_site_envelope_has_no_cell_that_fits_with_swelling(reports):
    # A finding, not a wish: if this starts passing, the design document must change.
    assert not reports["A"]["cell"]["ok"]


def test_button_and_microphone_land_where_the_hand_needs_them(reports):
    assert not reports["B"]["arc"]["problems"]


def test_wide_envelope_takes_the_largest_catalogue_cell_from_size_7_up():
    rows = {r["us_size"]: r["best_cell"] for r in size_sweep("B")}
    assert all(rows[s] == "grp1707_29" for s in range(7, 14))
    assert rows[6] is not None


def test_every_part_of_the_circuit_is_in_the_model():
    from gen.design import build
    wanted = sorted(b for b in map(S.body_of, build()) if b)
    placed = sorted(pl.part for isl in S.ISLANDS for pl in isl.parts)
    assert placed == wanted and len(placed) > 50


def test_parts_are_complete():
    parts = S.load_parts()
    for group in ("parts", "cells"):
        for key, part in parts[group].items():
            assert part["mpn"] and part["manufacturer"], key
            assert len(part["size"]) == 3 and all(v > 0 for v in part["size"]), key
            assert part["status"] in {"verified", "secondary", "unverified"}, key
    used = {pl.part for isl in S.ISLANDS for pl in isl.parts}
    assert used <= set(parts["parts"])
