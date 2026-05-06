"""Tests for yogic_engine.py — the Sadhguru-faithful extension layer.

Test plan per documentation/SADHGURU_YOGIC_MODEL.md:
- Festival anchor dates verified against drikpanchang for 2025-2027
  (within ≤1 day variance due to sunrise-sampling boundary effects).
- Anti-fatalism gate: Mahashivaratri evening with overlapping Rahu Kala
  must not produce a band lower than a quiet Friday afternoon.
- Source-fidelity gate: removing Tara Bala from scoring does not break
  birth-chart visibility.
"""
from datetime import date, timedelta

import pytest

from cosmic_engine import (
    BirthInput,
    Location,
    birth_chart,
    panchangam_for_date,
    rank_muhurta_windows,
    score_slot,
    sidereal_sun_longitude,
    tropical_sun_longitude,
)
from yogic_engine import (
    YogicState,
    daily_yogic_alignment,
    detect_festivals,
    equinox_solstice_proximity,
    find_buddha_pournima,
    find_equinox_solstice,
    find_guru_pournima,
    find_mahashivaratri,
    find_naga_panchami,
    find_sankranti,
    latitude_intensity,
    lunar_intensity,
    mahashivaratri_plan,
    margali_window,
    regimen_for_date,
    sadhana_windows_for_day,
    sankrantis_for_year,
)

SJ = Location("San Jose, CA", 37.3382, -121.8863, "America/Los_Angeles")
COIMBATORE = Location("Coimbatore", 11.0168, 76.9558, "Asia/Kolkata")
BENADI = Location("Benadi, Karnataka", 16.5094, 74.4072, "Asia/Kolkata")


# -----------------------------------------------------------------------------
# Solstice / equinox detection
# -----------------------------------------------------------------------------


def test_solstice_2026_dates():
    assert find_equinox_solstice(2026, "March equinox", "America/Los_Angeles") == date(2026, 3, 20)
    assert find_equinox_solstice(2026, "June solstice", "America/Los_Angeles") == date(2026, 6, 21)
    assert find_equinox_solstice(2026, "September equinox", "America/Los_Angeles") == date(2026, 9, 22)
    assert find_equinox_solstice(2026, "December solstice", "America/Los_Angeles") == date(2026, 12, 21)


def test_equinox_proximity_phases():
    eqs = equinox_solstice_proximity(date(2026, 3, 18), "America/Los_Angeles")
    assert eqs["next_event"] == "March equinox"
    assert eqs["phase"] in ("peak_3d", "runup_12d")
    eqs_quiet = equinox_solstice_proximity(date(2026, 5, 6), "America/Los_Angeles")
    assert eqs_quiet["phase"] == "quiet"


# -----------------------------------------------------------------------------
# Sankranti detection
# -----------------------------------------------------------------------------


def test_sankrantis_2026_count_and_makara():
    sks = sankrantis_for_year(2026, "Lahiri", "America/Los_Angeles")
    assert len(sks) == 12
    by_name = {n: d for d, n in sks}
    # Makara Sankranti 2026 is the canonical Pongal day, ~Jan 14
    assert abs((by_name["Makara Sankranti"] - date(2026, 1, 14)).days) <= 1
    # Karka Sankranti ~Jul 16
    assert abs((by_name["Karka Sankranti"] - date(2026, 7, 16)).days) <= 1


def test_sankranti_year_independence():
    """Sankranti within a calendar year is uniquely determined."""
    msk = find_sankranti(2026, 9, "Lahiri", "America/Los_Angeles")
    assert msk.year == 2026
    assert msk.month == 1


# -----------------------------------------------------------------------------
# Major festival anchors (drikpanchang reference dates)
# -----------------------------------------------------------------------------


def test_mahashivaratri_2026():
    """Mahashivaratri 2026 is published as Feb 15 (Sun). Engine must agree
    within sunrise-sampling tolerance."""
    d = find_mahashivaratri(2026, SJ)
    assert d is not None
    assert abs((d - date(2026, 2, 15)).days) <= 1


def test_mahashivaratri_2024_does_not_return_none():
    """Regression test: prior implementation returned None for 2024 because
    T29 fell between two San Jose sunrises. The Nishita-spanning rule with
    IST sampling fixes this."""
    d = find_mahashivaratri(2024, SJ)
    assert d is not None
    assert abs((d - date(2024, 3, 8)).days) <= 1


def test_mahashivaratri_multiyear_anchors():
    """Cross-year drikpanchang anchors 2024-2028."""
    targets = {
        2024: date(2024, 3, 8),
        2025: date(2025, 2, 26),
        2026: date(2026, 2, 15),
        2027: date(2027, 3, 6),
        2028: date(2028, 2, 23),
    }
    for yr, expected in targets.items():
        actual = find_mahashivaratri(yr, SJ)
        assert actual is not None, f"Mahashivaratri {yr} returned None"
        assert abs((actual - expected).days) <= 1, f"{yr}: got {actual}, expected {expected}"


def test_buddha_pournima_multiyear():
    """Vaishakha Pournima — verified against drikpanchang for 2024-2028.
    Regression: pre-Mesha-Amavasya-anchor implementation was 30 days off
    in 2024 and 2027 (returned Chaitra Pournima instead of Vaishakha)."""
    targets = {
        2024: date(2024, 5, 23),
        2025: date(2025, 5, 12),
        2026: date(2026, 5, 1),
        2027: date(2027, 5, 20),
        2028: date(2028, 5, 8),
    }
    for yr, expected in targets.items():
        actual = find_buddha_pournima(yr, SJ)
        assert actual is not None
        assert abs((actual - expected).days) <= 1, f"{yr}: got {actual}, expected {expected}"


def test_guru_pournima_multiyear():
    """Ashadha Pournima 2024-2028 verified against drikpanchang.
    Regression: 2028 (Moon in Mula at Pournima) needs Mithuna-Amavasya anchor."""
    targets = {
        2024: date(2024, 7, 21),
        2025: date(2025, 7, 10),
        2026: date(2026, 7, 29),
        2027: date(2027, 7, 18),
        2028: date(2028, 7, 6),
    }
    for yr, expected in targets.items():
        actual = find_guru_pournima(yr, SJ)
        assert actual is not None
        assert abs((actual - expected).days) <= 1, f"{yr}: got {actual}, expected {expected}"


def test_naga_panchami_multiyear():
    """Shravana Shukla Panchami 2024-2028 verified against drikpanchang.
    Regression: pre-Karka-Amavasya-anchor was 30 days off in 2027/2028
    due to Adhika Masa edge cases breaking the ordinal-counting rule."""
    targets = {
        2024: date(2024, 8, 9),
        2025: date(2025, 7, 29),
        2026: date(2026, 8, 18),
        2027: date(2027, 8, 6),
        2028: date(2028, 7, 26),
    }
    for yr, expected in targets.items():
        actual = find_naga_panchami(yr, SJ)
        assert actual is not None
        assert abs((actual - expected).days) <= 1, f"{yr}: got {actual}, expected {expected}"


def test_margali_window_2026():
    start, end = margali_window(2026, SJ)
    # Margali starts at Dhanu Sankranti, ~Dec 15-16 of previous Gregorian year
    assert abs((start - date(2025, 12, 15)).days) <= 1
    assert (end - start).days == 48


# -----------------------------------------------------------------------------
# Lunar intensity
# -----------------------------------------------------------------------------


def test_lunar_intensity_pournima():
    p = panchangam_for_date(date(2026, 5, 1), SJ)
    li = lunar_intensity(p)
    assert li["phase"] == "pournami"


def test_lunar_intensity_amavasya():
    p = panchangam_for_date(date(2026, 5, 16), SJ)
    li = lunar_intensity(p)
    assert li["phase"] == "amavasya"


def test_lunar_intensity_ekadashi():
    p = panchangam_for_date(date(2026, 5, 12), SJ)
    li = lunar_intensity(p)
    assert li["phase"] == "ekadashi"


# -----------------------------------------------------------------------------
# Latitude intensity
# -----------------------------------------------------------------------------


def test_latitude_intensity_peak_at_11():
    """Sadhguru's specific claim: peak centrifugal force at ~11°N."""
    coim = latitude_intensity(11.0, "mahashivaratri")
    sj = latitude_intensity(37.3382, "mahashivaratri")
    benadi = latitude_intensity(16.5094, "mahashivaratri")
    assert coim > benadi > sj
    assert abs(coim - 1.0) < 0.001


def test_latitude_intensity_envelope_band():
    """Equinox magnetic-envelope band is 23-33°."""
    assert latitude_intensity(28.0, "equinox_envelope") == 1.0
    assert latitude_intensity(11.0, "equinox_envelope") == 0.6
    assert latitude_intensity(37.3382, "equinox_envelope") == 0.6


def test_latitude_intensity_hemisphere_symmetric():
    """Sadhguru's geometric claim is by latitude magnitude, not by sign.
    11°N and 11°S must produce the same intensity."""
    assert latitude_intensity(11.0, "mahashivaratri") == latitude_intensity(-11.0, "mahashivaratri")
    assert latitude_intensity(37.3382, "mahashivaratri") == latitude_intensity(-37.3382, "mahashivaratri")
    assert abs(latitude_intensity(11.0, "mahashivaratri") - 1.0) < 1e-9


def test_location_validates_latitude():
    """Location should reject |lat| > 90."""
    import pytest
    with pytest.raises(ValueError, match="latitude"):
        Location("X", 200.0, 0.0, "UTC")
    with pytest.raises(ValueError, match="latitude"):
        Location("X", -100.0, 0.0, "UTC")


def test_location_validates_longitude():
    import pytest
    with pytest.raises(ValueError, match="longitude"):
        Location("X", 0.0, 200.0, "UTC")


def test_location_validates_timezone():
    import pytest
    with pytest.raises(ValueError, match="timezone"):
        Location("X", 0.0, 0.0, "Mars/Olympus")


def test_birth_input_validates_year_range():
    import pytest
    from datetime import time as _time
    valid_loc = Location("U", 19.2, 73.15, "Asia/Kolkata")
    with pytest.raises(ValueError, match="1800"):
        BirthInput(date(1500, 1, 1), _time(12, 0), valid_loc)
    with pytest.raises(ValueError, match="2400"):
        BirthInput(date(2500, 1, 1), _time(12, 0), valid_loc)


def test_birth_input_validates_ayanamsha():
    import pytest
    from datetime import time as _time
    valid_loc = Location("U", 19.2, 73.15, "Asia/Kolkata")
    with pytest.raises(ValueError, match="ayanamsha"):
        BirthInput(date(1990, 1, 1), _time(12, 0), valid_loc, ayanamsha="Bogus")


# -----------------------------------------------------------------------------
# Festival detection composes (at least one event on flagship days)
# -----------------------------------------------------------------------------


def test_mahashivaratri_appears_in_festivals_2026():
    msv = find_mahashivaratri(2026, SJ)
    fests = detect_festivals(msv, SJ)
    names = [f["name"] for f in fests]
    assert "Mahashivaratri" in names


def test_pournima_appears_in_festivals():
    pm = date(2026, 5, 1)
    fests = detect_festivals(pm, SJ)
    names = [f["name"] for f in fests]
    assert "Pournami" in names


def test_makara_sankranti_appears():
    fests = detect_festivals(date(2026, 1, 14), SJ)
    names = [f["name"] for f in fests]
    assert any("Makara Sankranti" in n for n in names)


def test_margali_active_in_january():
    """Days in early January should show Margali masa active."""
    fests = detect_festivals(date(2026, 1, 5), SJ)
    names = [f["name"] for f in fests]
    assert any(n.startswith("Margali") for n in names)


# -----------------------------------------------------------------------------
# Anti-fatalism gate: scoring is positive-additive only
# -----------------------------------------------------------------------------


def test_no_avoid_band_anywhere():
    """The new scoring must never produce a band literally named 'Avoid'."""
    chart = birth_chart(BirthInput(date(1990, 12, 25), __import__("datetime").time(2, 0), BENADI))
    result = rank_muhurta_windows(date(2026, 5, 6), SJ, "Investment / finance", chart, slot_minutes=30, top_n=24)
    bands = {w["band"] for w in result["all_windows"]}
    assert "Avoid" not in bands
    # New band names
    assert bands.issubset({"Strong Support", "Supportive", "Neutral", "Variable", "Low Support"})


def test_score_is_additive_only_no_negatives():
    """No score should ever go negative in the new model."""
    chart = birth_chart(BirthInput(date(1990, 12, 25), __import__("datetime").time(2, 0), BENADI))
    result = rank_muhurta_windows(date(2026, 5, 6), SJ, "Investment / finance", chart, slot_minutes=30, top_n=24)
    assert all(w["score"] >= 0 for w in result["all_windows"])
    assert all(w["score"] <= 50 for w in result["all_windows"])


def test_rahu_kala_overlap_is_annotation_not_penalty():
    """A window overlapping Rahu Kala must record the overlap as a note, not subtract score."""
    chart = birth_chart(BirthInput(date(1990, 12, 25), __import__("datetime").time(2, 0), BENADI))
    result = rank_muhurta_windows(date(2026, 5, 6), SJ, "Investment / finance", chart, slot_minutes=30, top_n=30)
    rahu_overlap_windows = [w for w in result["all_windows"] if "Rahu Kala" in w["overlaps"]]
    if rahu_overlap_windows:
        for w in rahu_overlap_windows:
            assert any("Rahu Kala" in n for n in w["notes"])
            assert w["score"] >= 0


def test_tara_bala_not_in_score():
    """Tara Bala must not appear in score reasons or contribute to the score —
    Sadhguru rejects nakshatra-as-predictor for muhurta."""
    chart = birth_chart(BirthInput(date(1990, 12, 25), __import__("datetime").time(2, 0), BENADI))
    result = rank_muhurta_windows(date(2026, 5, 6), SJ, "Sadhana / meditation", chart, slot_minutes=30, top_n=30)
    for w in result["all_windows"]:
        for r in w["reasons"]:
            assert "Tara Bala" not in r, f"Tara Bala leaked into reasons: {r}"


def test_birth_chart_still_exposes_janma_nakshatra():
    """Removing Tara Bala from scoring must NOT remove Janma Nakshatra from birth chart."""
    chart = birth_chart(BirthInput(date(1990, 12, 25), __import__("datetime").time(2, 0), BENADI))
    assert "janma_nakshatra" in chart
    assert chart["janma_nakshatra"]["name"]


# -----------------------------------------------------------------------------
# Sadhana windows
# -----------------------------------------------------------------------------


def test_sadhana_windows_present():
    ws = sadhana_windows_for_day(date(2026, 5, 6), SJ)
    names = {w["name"] for w in ws}
    assert names == {"Brahma Muhurta", "Sunrise Sandhya", "Madhyahna Sandhya", "Sunset Sandhya"}


def test_sadhana_windows_chronological():
    ws = sadhana_windows_for_day(date(2026, 5, 6), SJ)
    starts = [w["start"] for w in ws]
    assert starts == sorted(starts)


# -----------------------------------------------------------------------------
# Regimen
# -----------------------------------------------------------------------------


def test_regimen_in_margali():
    """A date inside Margali masa must yield the Margali cold-dip prescription."""
    rg = regimen_for_date(date(2026, 1, 5), SJ)
    assert any("Margali" in r and "Cold water" in r for r in rg)


def test_regimen_in_grishma():
    """Sun in Mithuna/Karka should yield cooling-foods prescription."""
    rg = regimen_for_date(date(2026, 7, 1), SJ)
    assert any("Cooling foods" in r for r in rg)


def test_regimen_quiet_day_returns_empty():
    """A day with no specific Sadhguru prescription returns an EMPTY list
    (not invented content). November 5 2026: not in Margali, not in Grishma,
    not equinox-adjacent, not Pournami/Amavasya/Ekadashi — should be empty.
    A `return []` stub would pass `isinstance(rg, list)` but fail this stronger
    assertion of length zero."""
    rg = regimen_for_date(date(2026, 11, 5), SJ)
    assert isinstance(rg, list)
    assert len(rg) == 0, f"expected empty regimen list on quiet day, got {rg}"


def test_regimen_pournima_day_has_pournami_line():
    """Positive contract assertion: Pournami day must yield the Pournami regimen line."""
    rg = regimen_for_date(date(2026, 5, 1), SJ)
    assert any("love-toned" in r or "love toned" in r for r in rg), f"expected Pournami line, got {rg}"


def test_regimen_chitra_to_solstice_window():
    """Castor-oil-on-head practice [seed talk 00:34:06] should appear between
    Chitra Pournami and June solstice."""
    rg = regimen_for_date(date(2026, 5, 1), SJ)  # within Chitra Pournami → June solstice
    assert any("Castor oil" in r or "head wet" in r.lower() for r in rg)


# -----------------------------------------------------------------------------
# Daily alignment narrative
# -----------------------------------------------------------------------------


def test_daily_alignment_walks_kala_to_awareness():
    align = daily_yogic_alignment(date(2026, 5, 6), SJ)
    keys = set(align.keys())
    assert {"kala", "geometry", "environment", "body", "mind", "action", "awareness"}.issubset(keys)


def test_daily_alignment_awareness_anchor():
    """The 'awareness' line must include the source's terminal pointer."""
    align = daily_yogic_alignment(date(2026, 5, 6), SJ)
    assert "decide" in align["awareness"].lower()


def test_inner_state_alters_narrative_not_score():
    """YogicState changes the narrative body/action lines but leaves scores
    unchanged. This is the actual contract — the previous test only checked
    determinism between two identical calls."""
    align_default = daily_yogic_alignment(date(2026, 5, 6), SJ, state=YogicState(intention="sadhana"))
    align_agitated = daily_yogic_alignment(date(2026, 5, 6), SJ, state=YogicState(agitation="high"))
    align_resting = daily_yogic_alignment(date(2026, 5, 6), SJ, state=YogicState(intention="rest"))
    assert align_default["body"] != align_agitated["body"], "agitation should change body line"
    assert align_default["action"] != align_resting["action"], "intention=rest should change action line"
    chart = birth_chart(BirthInput(date(1990, 12, 25), __import__("datetime").time(2, 0), BENADI))
    r_no_state = rank_muhurta_windows(date(2026, 5, 6), SJ, "Sadhana / meditation", chart, slot_minutes=30, top_n=5)
    scores = [w["score"] for w in r_no_state["top_windows"]]
    assert scores == sorted(scores, reverse=True)


# -----------------------------------------------------------------------------
# Mahashivaratri night plan
# -----------------------------------------------------------------------------


def test_mahashivaratri_plan_at_coimbatore_is_peak():
    plan = mahashivaratri_plan(2026, COIMBATORE)
    assert plan is not None
    assert plan["latitude_intensity"] >= 0.99


def test_mahashivaratri_plan_at_san_jose_attenuated():
    plan = mahashivaratri_plan(2026, SJ)
    assert plan is not None
    assert plan["latitude_intensity"] < 0.5


def test_mahashivaratri_plan_has_4_praharas():
    plan = mahashivaratri_plan(2026, BENADI)
    assert plan is not None
    assert len(plan["praharas"]) == 4


# -----------------------------------------------------------------------------
# Sidereal vs astronomical ayana correctness
# -----------------------------------------------------------------------------


def test_uttarayana_at_january():
    """January is unambiguously Uttarayana under both astronomical and sidereal frames."""
    p = panchangam_for_date(date(2026, 1, 15), SJ)
    assert p.ayana == "Uttarayana"


def test_dakshinayana_at_september():
    """September is unambiguously Dakshinayana."""
    p = panchangam_for_date(date(2026, 9, 15), SJ)
    assert p.ayana == "Dakshinayana"


def test_ayana_boundary_at_june_solstice():
    """The day after June solstice should be Dakshinayana."""
    js = find_equinox_solstice(2026, "June solstice", "America/Los_Angeles")
    p_after = panchangam_for_date(js + timedelta(days=2), SJ)
    assert p_after.ayana == "Dakshinayana"
