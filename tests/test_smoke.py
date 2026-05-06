from datetime import date, time

from cosmic_engine import BirthInput, Location, birth_chart, panchangam_for_date, rank_muhurta_windows

SAN_JOSE = Location("San Jose, CA", 37.3382, -121.8863, "America/Los_Angeles")
MUMBAI = Location("Mumbai, India", 19.0760, 72.8777, "Asia/Kolkata")


def test_panchangam_smoke():
    day = panchangam_for_date(date(2026, 5, 2), SAN_JOSE)
    assert day.tithi["index"] >= 1
    assert day.nakshatra["name"]
    assert day.sunrise


def test_birth_chart_smoke():
    chart = birth_chart(BirthInput(date(1990, 1, 1), time(12, 0), MUMBAI))
    assert chart["janma_nakshatra"]["name"]
    assert "Sun" in chart["planets"]


def test_muhurta_smoke():
    chart = birth_chart(BirthInput(date(1990, 1, 1), time(12, 0), MUMBAI))
    result = rank_muhurta_windows(date(2026, 5, 2), SAN_JOSE, "Sadhana / meditation", chart)
    assert len(result["top_windows"]) > 0
    assert 0 <= result["top_windows"][0]["score"] <= 100
