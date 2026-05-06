"""User-facing runner for Sadhguru-faithful yogic analysis.

Produces day / week / month / year reports for one or more birth charts.
Output is awareness-oriented — sadhana windows, festival markers, ritu
posture, equinox proximity. It does NOT produce personal predictions
(career, kids, visa, finances) — Sadhguru explicitly opposes that frame.

Usage:
    python run_yogic_analysis.py
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from cosmic_engine import (
    BirthInput,
    Location,
    birth_chart,
    panchangam_for_date,
    rank_muhurta_windows,
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

# -----------------------------------------------------------------------------
# Profiles (loaded from ~/.claude/CLAUDE.md notes; birth times confirmed)
# -----------------------------------------------------------------------------

ULHASNAGAR = Location("Ulhasnagar, Thane, Maharashtra", 19.2183, 73.1500, "Asia/Kolkata")
BENADI = Location("Benadi, Chikodi, Belgaum, Karnataka", 16.5094, 74.4072, "Asia/Kolkata")
SAN_JOSE = Location("San Jose, CA", 37.3382, -121.8863, "America/Los_Angeles")

AMOL = BirthInput(date(1990, 12, 25), time(2, 0), ULHASNAGAR, "Lahiri")
ANITA = BirthInput(date(1992, 6, 29), time(16, 0), BENADI, "Lahiri")


# -----------------------------------------------------------------------------
# Section helpers
# -----------------------------------------------------------------------------


def _hr(s: str) -> str:
    return "\n" + "=" * 78 + "\n" + s + "\n" + "=" * 78


def _sub(s: str) -> str:
    return "\n--- " + s + " ---"


def _line(s: str = "") -> None:
    print(s)


def _summary_birth(name: str, chart: Dict[str, Any]) -> None:
    _line(f"\n{name}:")
    _line(f"  Birth        : {chart['birth_datetime']} @ {chart['location']['name']}")
    _line(f"  Janma Nakshatra : {chart['janma_nakshatra']['name']} pada {chart['janma_nakshatra']['pada']} (lord {chart['janma_nakshatra']['lord']})")
    _line(f"  Janma Rashi  : {chart['janma_rashi']}")
    if chart.get("lagna"):
        _line(f"  Lagna        : {chart['lagna']['rashi']}  (±30-60 min birth-time uncertainty unaffected — rectified per user)")
    _line(f"  Sun          : {chart['planets']['Sun']['rashi']} / {chart['planets']['Sun']['nakshatra']['name']}")
    _line(f"  Moon         : {chart['planets']['Moon']['rashi']} / {chart['planets']['Moon']['nakshatra']['name']}")
    _line(f"  Note: Janma Nakshatra is shown for descriptive completeness. Per the Sadhguru-faithful")
    _line(f"        contract, nakshatra-matching does NOT drive window scoring (see SADHGURU_YOGIC_MODEL.md).")


# -----------------------------------------------------------------------------
# Day / Week / Month / Year sections
# -----------------------------------------------------------------------------


def day_view(d: date, loc: Location, label: str, state: Optional[YogicState] = None) -> None:
    _line(_hr(f"DAY  —  {d.isoformat()} ({d.strftime('%A')}) at {loc.name}"))
    p = panchangam_for_date(d, loc)
    li = lunar_intensity(p)
    eqs = equinox_solstice_proximity(d, loc.timezone)
    festivals = detect_festivals(d, loc)
    regimen = regimen_for_date(d, loc)
    align = daily_yogic_alignment(d, loc, state=state)
    sadhana_windows = sadhana_windows_for_day(d, loc)

    _line(f"Sunrise : {p.sunrise[11:16]}    Sunset : {p.sunset[11:16]}    Vara : {p.vara}")
    _line(f"Tithi   : {p.paksha} {p.tithi['name']}    Nakshatra: {p.nakshatra['name']} P{p.nakshatra['pada']}")
    _line(f"Yoga    : {p.yoga['name']}    Karana : {p.karana['name']}")
    _line(f"Sun     : {p.sun_rashi}    Moon : {p.moon_rashi}")
    _line(f"Ayana   : {p.ayana} (astronomical solstice frame)    Ritu : {p.ritu} (sidereal Sankranti frame)")
    _line(f"Lunar   : {li['phase']} — {li['quality']}")
    _line(f"Equinox/solstice: next {eqs['next_event']} in {eqs['days_until']} days ({eqs['phase']})")
    _line(f"Latitude intensity (Mahashivaratri model): {latitude_intensity(loc.latitude, 'mahashivaratri'):.2f} of peak (peak = 11°N)")

    _line(_sub("Festivals / yogic events today"))
    if festivals:
        for f in festivals:
            _line(f"  • {f['name']}  [{f['type']}]")
            _line(f"      rule: {f['rule']}")
            _line(f"      note: {f['note']}")
    else:
        _line("  (none)")

    _line(_sub("Sadhana windows (Brahma Muhurta + 3 Sandhyas)"))
    for w in sadhana_windows:
        _line(f"  {w['start'][11:16]}–{w['end'][11:16]}  {w['name']:18s}  {w['note']}")

    _line(_sub("Sadhguru-stated regimen for today"))
    if regimen:
        for r in regimen:
            _line(f"  • {r}")
    else:
        _line("  (no Sadhguru-specific regimen item maps to this date)")

    _line(_sub("Daily alignment narrative — Kala -> Awareness chain"))
    for k in ("kala", "geometry", "environment", "body", "mind", "action", "awareness"):
        _line(f"  {k.upper():12s}: {align[k]}")


def week_view(start: date, loc: Location) -> None:
    _line(_hr(f"WEEK  —  {start.isoformat()} through {(start + timedelta(days=6)).isoformat()} at {loc.name}"))
    _line(f"{'Date':12s} {'Vara':10s} {'Tithi':25s} {'Nakshatra':16s} {'Yoga':14s} {'Lunar':14s} Festivals")
    _line("-" * 110)
    for i in range(7):
        d = start + timedelta(days=i)
        p = panchangam_for_date(d, loc)
        li = lunar_intensity(p)
        festivals = detect_festivals(d, loc)
        f_str = "; ".join(f["name"] for f in festivals[:3]) if festivals else ""
        tithi_label = f"{'Sh' if p.paksha == 'Shukla' else 'Kr'} {p.tithi['name']}"
        _line(f"{d.isoformat():12s} {p.vara:10s} {tithi_label:25s} {p.nakshatra['name']:16s} {p.yoga['name']:14s} {li['phase']:14s} {f_str}")


def month_view(year: int, month: int, loc: Location) -> None:
    if month == 12:
        next_month_start = date(year + 1, 1, 1)
    else:
        next_month_start = date(year, month + 1, 1)
    days_in_month = (next_month_start - date(year, month, 1)).days
    _line(_hr(f"MONTH  —  {date(year, month, 1).strftime('%B %Y')} ({days_in_month} days)  at  {loc.name}"))

    _line(_sub("Festival / vrata calendar"))
    seen = set()
    for i in range(days_in_month):
        d = date(year, month, 1) + timedelta(days=i)
        festivals = detect_festivals(d, loc)
        for f in festivals:
            key = (d, f["name"])
            if key in seen:
                continue
            seen.add(key)
            if f["type"] in ("lunar", "lunar+solar", "solar", "sandhi", "solar+sadhana"):
                if f["name"].startswith("Margali"):
                    continue
                _line(f"  {d.isoformat()} {d.strftime('%a')}  {f['name']:30s}  ({f['rule']})")

    msv_start, msv_end = margali_window(year if month != 12 else year + 1, loc)
    if (date(year, month, 1) <= msv_end and next_month_start - timedelta(days=1) >= msv_start):
        _line(_sub("Margali masa overlap (Sadhguru-prescribed mandala)"))
        _line(f"  Margali start: {msv_start.isoformat()}    End-of-mandala: {msv_end.isoformat()}")
        _line(f"  Practice: cold water dip before sunrise at Brahma Muhurta")

    _line(_sub("Sadhana days this month — Pournami, Amavasya, Ekadashi"))
    for i in range(days_in_month):
        d = date(year, month, 1) + timedelta(days=i)
        p = panchangam_for_date(d, loc)
        idx = p.tithi["index"]
        if idx in (15, 30, 11, 26):
            li = lunar_intensity(p)
            _line(f"  {d.isoformat()} {d.strftime('%a')}  {li['phase']:12s}  {li['quality']}")


def year_view(year: int, loc: Location) -> None:
    _line(_hr(f"YEAR  —  {year}  at  {loc.name}"))

    _line(_sub("Astronomical solstices and equinoxes"))
    for kind in ("March equinox", "June solstice", "September equinox", "December solstice"):
        d = find_equinox_solstice(year, kind, loc.timezone)
        _line(f"  {d.isoformat()} {d.strftime('%a')}  {kind}")

    _line(_sub("12 sidereal Sankrantis (Lahiri ayanamsha)"))
    for d, name in sankrantis_for_year(year, "Lahiri", loc.timezone):
        _line(f"  {d.isoformat()} {d.strftime('%a')}  {name}")

    _line(_sub("Major Sadhguru-emphasised festivals"))
    msv = find_mahashivaratri(year, loc)
    if msv:
        intensity = latitude_intensity(loc.latitude, "mahashivaratri")
        _line(f"  {msv.isoformat()}  Mahashivaratri  (latitude intensity here: {intensity:.2f}; peak at 11°N = 1.00)")
    bpm = find_buddha_pournima(year, loc)
    if bpm:
        _line(f"  {bpm.isoformat()}  Buddha Pournima")
    gpm = find_guru_pournima(year, loc)
    if gpm:
        _line(f"  {gpm.isoformat()}  Guru Pournima")
    npm = find_naga_panchami(year, loc)
    if npm:
        _line(f"  {npm.isoformat()}  Naga Panchami (kundalini frame)")
    msv_start, msv_end = margali_window(year, loc)
    _line(f"  {msv_start.isoformat()} → {msv_end.isoformat()}  Margali masa (48-day mandala)")

    _line(_sub("Pournima / Amavasya / Ekadashi total counts"))
    pournimas = amavasyas = ekadashis = 0
    d = date(year, 1, 1)
    end = date(year, 12, 31)
    while d <= end:
        p = panchangam_for_date(d, loc)
        idx = p.tithi["index"]
        if idx == 15:
            pournimas += 1
        elif idx == 30:
            amavasyas += 1
        elif idx in (11, 26):
            ekadashis += 1
        d += timedelta(days=1)
    _line(f"  {pournimas} Pournimas, {amavasyas} Amavasyas, {ekadashis} Ekadashis in {year}")

    _line(_sub("Year-level sadhana arc (per Sadhguru's Uttarayana / Dakshinayana frame)"))
    j_sol = find_equinox_solstice(year, "June solstice", loc.timezone)
    d_sol = find_equinox_solstice(year, "December solstice", loc.timezone)
    m_eq = find_equinox_solstice(year, "March equinox", loc.timezone)
    _line(f"  Uttarayana (harvest / receptivity): {date(year-1, 12, 22).isoformat()} → {j_sol.isoformat()}")
    _line(f"     Peak grace window: Makar Sankranti → March equinox  ≈  Jan 14 → {m_eq.isoformat()}")
    _line(f"  Dakshinayana (sadhana / purification): {j_sol.isoformat()} → {d_sol.isoformat()}")
    _line(f"     Sadhanapada arc: summer solstice → winter solstice  (Isha residential program window)")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def main(today: Optional[date] = None) -> None:
    today = today or date.today()
    _line(_hr("SADHGURU-FAITHFUL YOGIC ANALYSIS"))
    _line("Source-fidelity contract: documentation/SADHGURU_YOGIC_MODEL.md")
    _line(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    _line("Anchor date: " + today.isoformat())
    _line("Output frame: cosmic-geometry alignment + sadhana windows. NOT predictive personal forecasting.")

    _line(_hr("BIRTH CHARTS  (descriptive — not used in scoring)"))
    chart_amol = birth_chart(AMOL)
    chart_anita = birth_chart(ANITA)
    _summary_birth("Amol", chart_amol)
    _summary_birth("Anita", chart_anita)

    state_amol = YogicState(intention="sadhana")
    state_anita = YogicState(intention="sadhana")

    day_view(today, SAN_JOSE, "Today (San Jose)", state_amol)

    week_view(today, SAN_JOSE)

    month_view(today.year, today.month, SAN_JOSE)

    year_view(today.year, SAN_JOSE)

    _line(_hr("MAHASHIVARATRI NIGHT PLAN — next occurrence"))
    msv_year = today.year
    if today > find_mahashivaratri(today.year, SAN_JOSE):
        msv_year = today.year + 1
    plan = mahashivaratri_plan(msv_year, SAN_JOSE)
    if plan:
        _line(f"Date         : {plan['date']}")
        _line(f"Location     : {plan['location']}  ({plan['latitude']}°N)")
        _line(f"Sunset       : {plan['sunset'][11:16]}")
        _line(f"Next sunrise : {plan['next_sunrise'][11:16]}")
        _line(f"Latitude intensity at this location: {plan['latitude_intensity']}")
        _line(f"  -> {plan['intensity_note']}")
        _line(_sub("Four Praharas of the night"))
        for ph in plan["praharas"]:
            _line(f"  {ph['name']:11s}  {ph['start'][11:16]} - {ph['end'][11:16]}")
        _line(f"Brahma Muhurta the next morning: {plan['brahma_muhurta_next']}")
        _line(f"Prescription: {plan['prescription']}")

    _line(_hr("SOURCE-FIDELITY CAVEATS — read before acting on the above"))
    _line("1. This output reflects what Sadhguru's stated yogic perspective endorses:")
    _line("   cosmic-geometry observation, sadhana windows, festival calendar, ritu posture.")
    _line("2. It does NOT contain predictive personal forecasting. Sadhguru explicitly opposes that frame.")
    _line("   Predictions about kids / career / visa / EB1A / finances do not appear here by design.")
    _line("3. Tara Bala (nakshatra-matching) is excluded from window scoring per Sadhguru's stated")
    _line("   rejection of nakshatra-as-predictor. Janma Nakshatra remains visible as descriptive birth data.")
    _line("4. Rahu Kala / Yamaganda / Gulika Kala are surfaced as informational annotations only —")
    _line("   the seed talk explicitly criticises fatalistic avoidance of these windows.")
    _line("5. Festival dates are computed against drikpanchang for 2025-2027 with ≤1 day variance")
    _line("   (sunrise-sampling boundary effect on tithi). For ritual scheduling, cross-check against")
    _line("   a published Panchangam for the user's specific timezone.")
    _line("6. Birth times are confirmed-correct per user. Lagna, Janma Nakshatra, Janma Rashi are stable.")


if __name__ == "__main__":
    main()
