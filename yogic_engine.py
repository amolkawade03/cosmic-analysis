"""Sadhguru-faithful yogic extension of cosmic_engine.

Every feature in this module traces to a position Sadhguru has stated. See
`documentation/SADHGURU_YOGIC_MODEL.md` for the source-fidelity contract.

Anti-fatalism principle (seed talk [00:13:58]):
    "It is not about blaming the stars or the planet for everything that you
    do or you do not do. ... It is about enhancing your ability to respond."

This module produces awareness-oriented output (festivals, equinox proximity,
regimen, sadhana windows, lunar phase posture). It does NOT produce verdicts
or personal predictions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from math import exp, pi, sin
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import swisseph as swe

from cosmic_engine import (
    AYANAMSHA,
    Location,
    PanchangamDay,
    nakshatra_info,
    noaa_sunrise_sunset,
    normalize,
    panchangam_for_date,
    sidereal_lon,
    sidereal_sun_longitude,
    tithi_info,
    to_jd_utc,
    tropical_sun_longitude,
)


# -----------------------------------------------------------------------------
# Inner state input (narrative-only; never alters scores)
# -----------------------------------------------------------------------------


@dataclass
class YogicState:
    """Optional inner-state input. Per SOURCE_KEY_POINTS principle #3, the
    user is not separate from the calendar. This dataclass adapts the
    narrative output to the user's current condition. It does NOT alter
    scoring — Sadhguru's frame is awareness, not optimization.
    """

    sleep_quality: str = "normal"  # "low" / "normal" / "high"
    agitation: str = "normal"      # "low" / "normal" / "high"
    intention: str = "sadhana"     # "sadhana" / "harvest" / "rest"
    recent_practices: List[str] = field(default_factory=list)


# -----------------------------------------------------------------------------
# Astronomical solstice / equinox detection (tropical longitude crossings)
# -----------------------------------------------------------------------------


_EQ_SOLS_TARGETS = {
    "March equinox": 0.0,
    "June solstice": 90.0,
    "September equinox": 180.0,
    "December solstice": 270.0,
}


def _sun_tropical_lon_at(dt: datetime) -> float:
    return normalize(swe.calc_ut(to_jd_utc(dt), swe.SUN, swe.FLG_SWIEPH)[0][0])


def find_equinox_solstice(year: int, kind: str, tz: str = "UTC") -> date:
    """Find the date (in given tz) of the named astronomical equinox/solstice.

    Binary search on Sun's tropical longitude crossing the target value.
    """
    target = _EQ_SOLS_TARGETS[kind]
    seed = {
        "March equinox": date(year, 3, 20),
        "June solstice": date(year, 6, 21),
        "September equinox": date(year, 9, 22),
        "December solstice": date(year, 12, 21),
    }[kind]
    lo = datetime.combine(seed - timedelta(days=4), time(0, 0), ZoneInfo(tz))
    hi = datetime.combine(seed + timedelta(days=4), time(23, 59), ZoneInfo(tz))
    for _ in range(40):
        mid = lo + (hi - lo) / 2
        lon = _sun_tropical_lon_at(mid)
        diff = (lon - target + 540) % 360 - 180
        if diff < 0:
            lo = mid
        else:
            hi = mid
    return lo.astimezone(ZoneInfo(tz)).date()


def equinox_solstice_proximity(d: date, tz: str = "UTC") -> Dict[str, Any]:
    """Distance to the next astronomical equinox/solstice and a phase tag.

    Per Sadhguru: "this period from the equinox to solstice is important
    because this is the time the sun's impact is at its peak" — [00:33:50].
    The 12-day run-up window is a documented tunable, not a magic number.
    """
    candidates = []
    for offset in (0, 1):
        for kind in _EQ_SOLS_TARGETS:
            candidates.append((find_equinox_solstice(d.year + offset, kind, tz), kind))
    candidates.sort(key=lambda x: x[0])
    next_event = next(((dt, k) for dt, k in candidates if dt >= d), candidates[-1])
    last_event = next(((dt, k) for dt, k in reversed(candidates) if dt < d), candidates[0])
    days_until = (next_event[0] - d).days
    days_since = (d - last_event[0]).days
    if days_until <= 3:
        phase = "peak_3d"
    elif days_until <= 12:
        phase = "runup_12d"
    elif days_since <= 12:
        phase = "aftermath_12d"
    else:
        phase = "quiet"
    return {
        "next_event": next_event[1],
        "next_event_date": next_event[0].isoformat(),
        "days_until": days_until,
        "last_event": last_event[1],
        "last_event_date": last_event[0].isoformat(),
        "days_since": days_since,
        "phase": phase,
    }


# -----------------------------------------------------------------------------
# Sankranti detection (sidereal Sun crossing rashi boundaries)
# -----------------------------------------------------------------------------


_RASHI_NAMES = [
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena",
]


def find_sankranti(year: int, rashi_idx: int, ayanamsha: str = "Lahiri", tz: str = "UTC") -> date:
    """Date Sun crosses 0° of the named sidereal rashi in the given Gregorian year.

    Each rashi's Sankranti falls in a known calendar month; we seed the binary
    search from the 14th of that month and refine.
    """
    seed_month = {0: 4, 1: 5, 2: 6, 3: 7, 4: 8, 5: 9,
                  6: 10, 7: 11, 8: 12, 9: 1, 10: 2, 11: 3}[rashi_idx]
    seed = date(year, seed_month, 14)
    target = rashi_idx * 30.0
    lo = datetime.combine(seed - timedelta(days=4), time(0, 0), ZoneInfo(tz))
    hi = datetime.combine(seed + timedelta(days=4), time(23, 59), ZoneInfo(tz))
    for _ in range(40):
        mid = lo + (hi - lo) / 2
        lon = sidereal_lon(to_jd_utc(mid), swe.SUN, ayanamsha)
        diff = (lon - target + 540) % 360 - 180
        if diff < 0:
            lo = mid
        else:
            hi = mid
    return lo.astimezone(ZoneInfo(tz)).date()


def sankrantis_for_year(year: int, ayanamsha: str = "Lahiri", tz: str = "UTC") -> List[Tuple[date, str]]:
    """All 12 sidereal Sankrantis for the given Gregorian year."""
    out = []
    for idx, name in enumerate(_RASHI_NAMES):
        try:
            out.append((find_sankranti(year, idx, ayanamsha, tz), f"{name} Sankranti"))
        except Exception:
            pass
    out.sort()
    return out


# -----------------------------------------------------------------------------
# Festival / vrata detection
# -----------------------------------------------------------------------------


def lunar_intensity(panchangam: PanchangamDay) -> Dict[str, str]:
    """Classify the day's lunar posture per Sadhguru's framing.

    Pournami = wellbeing / love-toned / upward.
    Amavasya = liberation / base-toned / inward.
    Ekadashi = body's natural fasting day.
    Source: Isha "Difference Between Pournami and Amavasya"; "Ekadashi" article.
    """
    idx = panchangam.tithi["index"]
    if idx == 15:
        return {"phase": "pournami", "quality": "wellbeing / love-toned / upward",
                "note": "Subtle, pleasant pull; sadhana of receptivity"}
    if idx == 30:
        return {"phase": "amavasya", "quality": "liberation / base-toned / inward",
                "note": "Inward turn; rest, observation, sadhana of dissolution"}
    if idx in (11, 26):
        return {"phase": "ekadashi", "quality": "natural fasting day",
                "note": "If body is prepared: fast. Otherwise light food + sadhana"}
    if idx in (13, 28):
        return {"phase": "trayodashi", "quality": "preparation day",
                "note": "Pradosham window at sunset (general Shaiva tradition)"}
    if idx in (14, 29):
        return {"phase": "chaturdashi", "quality": "edge before Pournami / Amavasya",
                "note": "Energy gathering; preparation for the lunar peak"}
    if idx <= 15:
        return {"phase": "waxing", "quality": "active / outward",
                "note": "Shukla paksha — building energy"}
    return {"phase": "waning", "quality": "settling / inward",
            "note": "Krishna paksha — releasing energy"}


def _is_pournima_for_year(d: date, panchangam: PanchangamDay) -> bool:
    return panchangam.tithi["index"] == 15


def _moon_nakshatra_idx(panchangam: PanchangamDay) -> int:
    return panchangam.nakshatra["index"] - 1  # convert 1-based to 0-based


def _find_pournimas(start: date, end: date, loc: Location, ayanamsha: str = "Lahiri") -> List[Tuple[date, PanchangamDay]]:
    """Scan a date range and return all dates where tithi index is 15."""
    out = []
    d = start
    while d <= end:
        p = panchangam_for_date(d, loc, ayanamsha)
        if p.tithi["index"] == 15:
            out.append((d, p))
        d += timedelta(days=1)
    return out


def find_mahashivaratri(year: int, loc: Location, ayanamsha: str = "Lahiri") -> Optional[date]:
    """Krishna Chaturdashi (T29) when Sun is in sidereal Kumbha.

    Traditional rule: Phalguna Krishna Chaturdashi. Detection: scan Feb-March
    for T29 with Sun's sidereal longitude in [300°, 330°) (Kumbha). Returns
    None if no match (extremely rare).
    """
    d = date(year, 2, 1)
    end = date(year, 3, 31)
    while d <= end:
        p = panchangam_for_date(d, loc, ayanamsha)
        if p.tithi["index"] == 29:
            sun_lon = sidereal_sun_longitude(d, loc, ayanamsha)
            if 300.0 <= sun_lon < 330.0:
                return d
        d += timedelta(days=1)
    return None


def find_guru_pournima(year: int, loc: Location, ayanamsha: str = "Lahiri") -> Optional[date]:
    """Ashadha Pournima — Pournima with Moon in Purva Ashadha or Uttara Ashadha
    nakshatra. This is the canonical anchor: the Hindu lunar month of Ashadha
    is named after this nakshatra pair.

    Per Isha 'Story of Guru Purnima': "On the first full moon after the summer
    solstice, [Adiyogi] decided to teach." In years where the Ashadha Pournima
    falls just before the June solstice (rare), this is the next such Pournima.
    """
    pms = _find_pournimas(date(year, 6, 15), date(year, 8, 5), loc, ayanamsha)
    for d, p in pms:
        if p.nakshatra["name"] in ("Purva Ashadha", "Uttara Ashadha"):
            return d
    for d, p in pms:
        sun_lon = sidereal_sun_longitude(d, loc, ayanamsha)
        if 90.0 <= sun_lon < 120.0:
            return d
    return None


def find_buddha_pournima(year: int, loc: Location, ayanamsha: str = "Lahiri") -> Optional[date]:
    """Vaishakha Pournima — Pournima with Sun in sidereal Mesha (rashi 0).

    The Isha article frames this as "third purnima after the earth shifts to
    the northern run of the sun"; the unambiguous astronomical anchor is
    Vaishakha Pournima = Pournima with Sun in Mesha (Aries). For 2026 this
    is May 1.
    """
    pms = _find_pournimas(date(year, 4, 5), date(year, 5, 25), loc, ayanamsha)
    for d, _ in pms:
        sun_lon = sidereal_sun_longitude(d, loc, ayanamsha)
        if 0.0 <= sun_lon < 30.0:
            return d
    return None


def find_naga_panchami(year: int, loc: Location, ayanamsha: str = "Lahiri") -> Optional[date]:
    """Shravana Shukla Panchami.

    Detection: the second Shukla Panchami after the June solstice (the first
    one is Ashadha Shukla Panchami, the second is Shravana Shukla Panchami).
    Equivalent astronomical anchor: tithi 5 shukla in the lunar month
    following Ashadha Pournima.
    """
    js = find_equinox_solstice(year, "June solstice", loc.timezone)
    d = js
    end = date(year, 9, 5)
    found = []
    while d <= end:
        p = panchangam_for_date(d, loc, ayanamsha)
        if p.tithi["index"] == 5 and p.paksha == "Shukla":
            found.append(d)
        d += timedelta(days=1)
    return found[1] if len(found) >= 2 else (found[0] if found else None)


def margali_window(year: int, loc: Location, ayanamsha: str = "Lahiri") -> Tuple[date, date]:
    """Margali masa = Sun in sidereal Dhanu (Sagittarius, rashi 8).

    Per seed talk [00:39:10]: 'Tamil month of Margali starts on 16th December
    towards the end of Dakshinayana ... cold water dip before sunrise at
    Brahma Muhurtam ... do this for a whole mandela or a period of 40 to 48
    days.' Returns (Margali start, Margali start + 48 days mandala end).
    """
    start = find_sankranti(year - 1, 8, ayanamsha, loc.timezone)
    return start, start + timedelta(days=48)


def detect_festivals(d: date, loc: Location, ayanamsha: str = "Lahiri") -> List[Dict[str, str]]:
    """Festivals or yogic events active or imminent on date d."""
    events: List[Dict[str, str]] = []
    p = panchangam_for_date(d, loc, ayanamsha)
    li = lunar_intensity(p)

    if li["phase"] == "pournami":
        events.append({
            "name": "Pournami",
            "type": "lunar",
            "rule": "Tithi 15 (full moon)",
            "note": "Wellbeing / love-toned / upward (Isha: 'Pournami is sacred for wellbeing')",
        })
    if li["phase"] == "amavasya":
        events.append({
            "name": "Amavasya",
            "type": "lunar",
            "rule": "Tithi 30 (new moon)",
            "note": "Liberation / base-toned / inward (Isha: 'Amavasya is sacred for liberation')",
        })
    if li["phase"] == "ekadashi":
        events.append({
            "name": "Ekadashi",
            "type": "lunar",
            "rule": "Tithi 11 / 26",
            "note": "Body's natural fasting day in 40-48 day mandala (Isha: 'Why fast on Ekadashi')",
        })
    if li["phase"] == "trayodashi":
        events.append({
            "name": "Pradosham",
            "type": "sandhi",
            "rule": "Trayodashi (T13/T28) sunset window",
            "note": "General Shaiva tradition; not a primary Sadhguru emphasis. Sunset sandhya overlap is the safer Sadhguru-aligned surrogate.",
        })

    msv = find_mahashivaratri(d.year, loc, ayanamsha)
    if msv == d:
        events.append({
            "name": "Mahashivaratri",
            "type": "lunar+solar",
            "rule": "Krishna Chaturdashi with Sun in sidereal Kumbha",
            "note": "Natural upsurge of energy; spine-vertical all night; 11°N latitude is peak.",
        })

    gpm = find_guru_pournima(d.year, loc, ayanamsha)
    if gpm == d:
        events.append({
            "name": "Guru Pournima",
            "type": "lunar+solar",
            "rule": "First Pournami after June solstice",
            "note": "Adi Yogi turned south to teach; day to earn grace.",
        })

    bpm = find_buddha_pournima(d.year, loc, ayanamsha)
    if bpm == d:
        events.append({
            "name": "Buddha Pournima",
            "type": "lunar+solar",
            "rule": "3rd Pournami after Makara Sankranti",
            "note": "Significant for any spiritual aspirant (Isha: 'Buddha Pournami').",
        })

    npm = find_naga_panchami(d.year, loc, ayanamsha)
    if npm == d:
        events.append({
            "name": "Naga Panchami",
            "type": "lunar+solar",
            "rule": "Shukla Panchami with Sun in Karka / Simha",
            "note": "Snake = kundalini symbol; significant for meditators (Isha 'Naga Panchami').",
        })

    sids = sankrantis_for_year(d.year, ayanamsha, loc.timezone)
    for s_date, s_name in sids:
        if s_date == d:
            events.append({
                "name": s_name,
                "type": "solar",
                "rule": f"Sun crosses 0° sidereal {s_name.split()[0]}",
                "note": "Solar transition into a new rashi.",
            })

    msv_start, msv_end = margali_window(d.year + 1 if d.month == 12 and d.day >= 14 else d.year, loc, ayanamsha)
    if msv_start <= d <= msv_end:
        day_in_mandala = (d - msv_start).days + 1
        events.append({
            "name": f"Margali masa (day {day_in_mandala}/48)",
            "type": "solar+sadhana",
            "rule": "Sun in sidereal Dhanu (Sagittarius)",
            "note": "Cold water dip before sunrise at Brahma Muhurta; sustain 40-48 days for mandala.",
        })

    return events


# -----------------------------------------------------------------------------
# Latitude-intensity weighting (narrative-only, never scoring)
# -----------------------------------------------------------------------------


def latitude_intensity(latitude: float, kind: str) -> float:
    """0.0-to-1.0 scalar describing how strongly a Sadhguru-stated geometric
    effect manifests at the given latitude.

    kind = 'mahashivaratri': 1.0 at 11°N (Isha Yoga Center latitude),
        attenuated by Gaussian with sigma 15°. Sadhguru's claim:
        "maximum amount of centrifugal force happens at approximately
        eleven degrees latitude."

    kind = 'equinox_envelope': flat 1.0 inside 23-33°N, 0.6 outside.
        Sadhguru's claim: "particularly between 23 to 33 degree latitude
        this effect will be at its highest."
    """
    if kind == "mahashivaratri":
        sigma = 15.0
        return float(exp(-((latitude - 11.0) ** 2) / (2 * sigma ** 2)))
    if kind == "equinox_envelope":
        return 1.0 if 23.0 <= abs(latitude) <= 33.0 else 0.6
    return 1.0


# -----------------------------------------------------------------------------
# Sadhguru-stated regimen items (date-specific practices)
# -----------------------------------------------------------------------------


def regimen_for_date(d: date, loc: Location, ayanamsha: str = "Lahiri") -> List[str]:
    """Return Sadhguru-named practices for the date's cosmic configuration.

    This is NOT a generic 6-ritu Ayurvedic schema — only items the seed talk
    or Isha-published material specifically prescribe.
    """
    out: List[str] = []
    p = panchangam_for_date(d, loc, ayanamsha)
    sun_lon = sidereal_sun_longitude(d, loc, ayanamsha)
    eqs = equinox_solstice_proximity(d, loc.timezone)

    # Castor oil / wet head between Chitra Pournami and June solstice
    chitra_pm = None
    for pm_d, pm_p in _find_pournimas(date(d.year, 3, 25), date(d.year, 5, 15), loc, ayanamsha):
        if pm_p.nakshatra["name"] == "Chitra":
            chitra_pm = pm_d
            break
    js = find_equinox_solstice(d.year, "June solstice", loc.timezone)
    if chitra_pm and chitra_pm <= d <= js:
        out.append("Castor oil on top of head before going out (or keep top of head wet) — through summer solstice. [seed talk 00:34:06]")

    # Wet head during equinox peak / runup
    if eqs["phase"] in ("peak_3d", "runup_12d"):
        out.append("Keep hair / top of head wet, particularly during the four sandhyas. [seed talk 00:33:13]")

    # Cooling foods during Grishma (Sun in Mithuna / Karka, sidereal 60-120°)
    if 60.0 <= sun_lon < 120.0:
        out.append("Cooling foods rich in B12 — Lakshmi charu (Andhra) / palisadam (Tamil) / kuru (Karnataka), fresh seasonal. [seed talk 00:35:57]")

    # Margali cold dip
    msv_start, msv_end = margali_window(d.year + 1 if d.month == 12 and d.day >= 14 else d.year, loc, ayanamsha)
    if msv_start <= d <= msv_end:
        day_in_mandala = (d - msv_start).days + 1
        out.append(f"Cold water dip before sunrise at Brahma Muhurta — Margali day {day_in_mandala} of 48. [seed talk 00:39:10]")

    # Lunar phase items
    li = lunar_intensity(p)
    if li["phase"] == "ekadashi":
        out.append("Body's natural fasting day. If prepared: fast. Otherwise light food + sadhana. [Isha: Why Ekadashi]")
    elif li["phase"] == "pournami":
        out.append("Subtle love-toned upward pull. Subdued sadhana / receptivity / Dhyanalinga offering. [Isha: Pournami article]")
    elif li["phase"] == "amavasya":
        out.append("Inward base-toned downward pull. Rest, observation, dissolution sadhana. [Isha: Amavasya article]")

    return out


# -----------------------------------------------------------------------------
# Mahashivaratri night plan
# -----------------------------------------------------------------------------


def mahashivaratri_plan(year: int, loc: Location, ayanamsha: str = "Lahiri") -> Optional[Dict[str, Any]]:
    """Mahashivaratri night plan for the given year and location.

    Returns the four praharas (sunset → next sunrise / 4) and the next
    Brahma Muhurta. Latitude-intensity is included narratively.
    """
    d = find_mahashivaratri(year, loc, ayanamsha)
    if d is None:
        return None
    _, sunset = noaa_sunrise_sunset(d, loc)
    next_sunrise, _ = noaa_sunrise_sunset(d + timedelta(days=1), loc)
    night_len = next_sunrise - sunset
    prahara = night_len / 4
    praharas = [
        {"name": f"Prahara {i+1}", "start": (sunset + i * prahara).isoformat(),
         "end": (sunset + (i+1) * prahara).isoformat()}
        for i in range(4)
    ]
    intensity = latitude_intensity(loc.latitude, "mahashivaratri")
    return {
        "date": d.isoformat(),
        "location": loc.name,
        "latitude": loc.latitude,
        "latitude_intensity": round(intensity, 3),
        "intensity_note": (
            "Peak at 11°N. At your latitude the geometric effect is "
            f"~{round(intensity*100)}% of peak — Sadhguru's specific "
            "geometric claim: 'maximum centrifugal force happens at "
            "approximately eleven degrees latitude.'"
        ),
        "sunset": sunset.isoformat(),
        "next_sunrise": next_sunrise.isoformat(),
        "praharas": praharas,
        "brahma_muhurta_next": (next_sunrise - timedelta(minutes=96)).isoformat() + " — " + (next_sunrise - timedelta(minutes=48)).isoformat(),
        "prescription": "Spine vertical all night; cooperate with the upsurge.",
    }


# -----------------------------------------------------------------------------
# Daily yogic alignment narrative — Kala -> Awareness chain
# -----------------------------------------------------------------------------


def daily_yogic_alignment(d: date, loc: Location, ayanamsha: str = "Lahiri",
                          state: Optional[YogicState] = None) -> Dict[str, str]:
    """Narrative walking Kala -> Geometry -> Environment -> Body -> Mind ->
    Awareness, per SOURCE_KEY_POINTS principle #10.
    """
    p = panchangam_for_date(d, loc, ayanamsha)
    li = lunar_intensity(p)
    eqs = equinox_solstice_proximity(d, loc.timezone)
    festivals = detect_festivals(d, loc, ayanamsha)
    regimen = regimen_for_date(d, loc, ayanamsha)
    state = state or YogicState()

    festival_str = "; ".join(f["name"] for f in festivals) if festivals else "no specific festival today"
    regimen_str = " | ".join(regimen) if regimen else "(no Sadhguru-specific regimen item for this date)"

    body_lead = ""
    if state.agitation == "high":
        body_lead = "Agitation is up — start with pranayama or simple physical settling. "
    elif state.sleep_quality == "low":
        body_lead = "Sleep was thin — attenuate physical intensity, lean on stillness. "

    intent_note = {
        "sadhana": "Lean into Brahma Muhurta and Sandhya windows; the day's geometry is the runway.",
        "harvest": "Uttarayana posture: outward action, finishing, completing.",
        "rest": "Permit settling; the calendar accepts non-doing.",
    }[state.intention]

    return {
        "kala": (
            f"Day sits in {p.ayana} / {p.ritu}. "
            f"Lunar phase: {li['phase']} ({li['quality']}). "
            f"{eqs['days_until']} days to {eqs['next_event']} ({eqs['phase']})."
        ),
        "geometry": (
            f"Vara {p.vara}; {p.paksha} {p.tithi['name']}; "
            f"Moon in {p.nakshatra['name']} pada {p.nakshatra['pada']}; "
            f"Yoga {p.yoga['name']}; Karana {p.karana['name']}; "
            f"Sun {p.sun_rashi}, Moon {p.moon_rashi}."
        ),
        "environment": (
            f"Festivals / events: {festival_str}. "
            + (
                f"Equinox/solstice {eqs['phase']} — sun's impact heightened; head-wet practice optional."
                if eqs["phase"] in ("peak_3d", "runup_12d", "aftermath_12d") else
                "Cosmic geometry quiet; ordinary day."
            )
        ),
        "body": body_lead + ("Regimen: " + regimen_str),
        "mind": (
            f"{li['note']}. "
            "Observe the mind's posture before reacting; the day is a mirror, not a verdict."
        ),
        "action": intent_note,
        "awareness": (
            "The stars and the planets need not decide your experience of life. "
            "You and you alone should be the one to decide your inner experience. "
            "[seed talk 00:41:41]"
        ),
    }


# -----------------------------------------------------------------------------
# Sadhana windows — first-class sadhana-aligned timing for a day
# -----------------------------------------------------------------------------


SADHANA_WINDOW_NAMES = ["Brahma Muhurta", "Sunrise Sandhya", "Madhyahna Sandhya", "Sunset Sandhya"]


def sadhana_windows_for_day(d: date, loc: Location, ayanamsha: str = "Lahiri") -> List[Dict[str, str]]:
    """The day's primary sadhana windows, returned in chronological order with
    a one-line note per window. These are the windows Sadhguru consistently
    points to as 'do your practices here'.
    """
    p = panchangam_for_date(d, loc, ayanamsha)
    li = lunar_intensity(p)
    out = []
    for w in p.special_windows:
        if w["name"] in SADHANA_WINDOW_NAMES:
            note_extra = ""
            if li["phase"] == "pournami" and w["name"] in ("Sunset Sandhya", "Sunrise Sandhya"):
                note_extra = " | Pournami amplifies the sandhi."
            elif li["phase"] == "amavasya" and w["name"] == "Brahma Muhurta":
                note_extra = " | Amavasya inward turn is strongest at Brahma Muhurta."
            out.append({
                "name": w["name"],
                "start": w["start"],
                "end": w["end"],
                "note": _SADHANA_WINDOW_NOTES[w["name"]] + note_extra,
            })
    out.sort(key=lambda x: x["start"])
    return out


_SADHANA_WINDOW_NOTES = {
    "Brahma Muhurta": "Last quarter of night. Pineal at peak. Dramatic spiritual progress window.",
    "Sunrise Sandhya": "±20 min around sunrise. Body in flux; transcendence accessible.",
    "Madhyahna Sandhya": "True solar noon ±20 min. Third sandhi. Brief mid-day still point.",
    "Sunset Sandhya": "±20 min around sunset. Day-night transition; subtle pull stronger.",
}
