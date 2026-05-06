from datetime import date, datetime, time

from cosmic_engine import (
    BirthInput,
    Location,
    birth_chart,
    chandra_bala,
    panchangam_for_date,
    rank_muhurta_windows,
    tara_bala,
)

SAN_JOSE = Location("San Jose, CA", 37.3382, -121.8863, "America/Los_Angeles")
MUMBAI = Location("Mumbai, India", 19.0760, 72.8777, "Asia/Kolkata")


def test_daily_panchangam_has_valid_ranges_and_ordered_windows():
    day = panchangam_for_date(date(2026, 5, 2), SAN_JOSE)
    sunrise = datetime.fromisoformat(day.sunrise)
    sunset = datetime.fromisoformat(day.sunset)

    assert sunrise < sunset
    assert 1 <= day.tithi["index"] <= 30
    assert 1 <= day.nakshatra["index"] <= 27
    assert 1 <= day.nakshatra["pada"] <= 4
    assert 1 <= day.yoga["index"] <= 27
    assert day.special_windows

    for window in day.special_windows:
        start = datetime.fromisoformat(window["start"])
        end = datetime.fromisoformat(window["end"])
        assert start < end, window


def test_birth_chart_has_required_personalization_fields():
    chart = birth_chart(BirthInput(date(1990, 1, 1), time(12, 0), MUMBAI))

    assert chart["janma_rashi"]
    assert 1 <= chart["janma_rashi_index"] <= 12
    assert 1 <= chart["janma_nakshatra"]["index"] <= 27
    assert "Rahu" in chart["planets"]
    assert "Ketu" in chart["planets"]


def test_muhurta_windows_are_sorted_and_personalized():
    chart = birth_chart(BirthInput(date(1990, 1, 1), time(12, 0), MUMBAI))
    result = rank_muhurta_windows(
        date(2026, 5, 2),
        SAN_JOSE,
        "Investment / finance",
        chart,
        slot_minutes=30,
        top_n=10,
    )

    scores = [slot["score"] for slot in result["top_windows"]]
    assert scores == sorted(scores, reverse=True)
    assert result["top_windows"][0]["personal"]
    assert all(slot["start"] < slot["end"] for slot in result["top_windows"])


def test_tara_and_chandra_bala_known_support_flags():
    assert tara_bala(day_nak_idx=2, janma_nak_idx=1)["supportive"] is True
    assert tara_bala(day_nak_idx=3, janma_nak_idx=1)["supportive"] is False
    assert chandra_bala(day_moon_rashi_idx=3, janma_rashi_idx=1)["supportive"] is True
    assert chandra_bala(day_moon_rashi_idx=8, janma_rashi_idx=1)["ashtama_chandra"] is True
