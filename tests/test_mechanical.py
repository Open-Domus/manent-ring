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


def test_every_island_fits_radially(reports):
    bad = [i for i in reports["B"]["islands"] if not i["ok"]]
    assert not bad, bad


def test_wide_envelope_fits_a_catalogue_cell(reports):
    assert reports["B"]["ok"], reports["B"]


def test_site_envelope_has_no_cell_that_fits_with_swelling(reports):
    # A finding, not a wish: if this starts passing, the design document must change.
    assert not reports["A"]["cell"]["ok"]


def test_button_and_microphone_land_where_the_hand_needs_them(reports):
    assert not reports["B"]["arc"]["problems"]


def test_every_size_offered_has_a_cell_and_room_for_the_boards():
    rows = {r["us_size"]: r for r in size_sweep("B")}
    assert sorted(rows) == list(range(8, 14))
    assert all(r["best_cell"] for r in rows.values())
    assert all(r["islands_fit"] for r in rows.values())


def test_the_wider_cell_family_does_not_pass_with_swelling(reports):
    # A finding, not a wish: the 1.7 x 6.5 mm cells miss the swelling allowance by a hair.
    from manent_mech.checks import cell_report
    from manent_mech.params import WIDE
    assert not cell_report(WIDE, S.load_parts(), "grp1707_29")["ok"]


def test_the_flex_between_islands_is_long_enough_and_not_folded_too_tight(reports):
    assert all(b["ok"] for b in reports["B"]["bends"]), reports["B"]["bends"]


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
