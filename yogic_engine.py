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
from functools import lru_cache
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
# Hindu-calendar reference sampling
# -----------------------------------------------------------------------------
#
# Hindu festivals are calendar events tied to lunar/solar geometry; the canonical
# date is the Indian Standard Time (IST) date where the relevant tithi was active
# at sunrise. drikpanchang.com uses this convention. For a user in San Jose, the
# festival "date" should be the IST date — even if the user's local-clock
# observance starts the prior evening — so that the engine matches the global
# yogic event Isha publishes.
#
# `_INDIA_REF` is the location used for festival-date sampling regardless of the
# user's location. Coimbatore (11°N) is chosen because (a) it's Isha Yoga Center,
# (b) it lies at Sadhguru's stated peak-centrifugal-force latitude, and (c) it
# uses Asia/Kolkata timezone like all of India. The user's `Location` argument
# is preserved in detect_festivals etc. for sandhya/sunrise-overlap purposes.

_INDIA_REF = Location("Coimbatore (Hindu-calendar reference)", 11.0168, 76.9558, "Asia/Kolkata")


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


@lru_cache(maxsize=512)
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


@lru_cache(maxsize=512)
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


@lru_cache(maxsize=128)
def _sankrantis_for_year_cached(year: int, ayanamsha: str, tz: str) -> Tuple[Tuple[date, str], ...]:
    out: List[Tuple[date, str]] = []
    for idx, name in enumerate(_RASHI_NAMES):
        try:
            out.append((find_sankranti(year, idx, ayanamsha, tz), f"{name} Sankranti"))
        except Exception:
            pass
    out.sort()
    return tuple(out)


def sankrantis_for_year(year: int, ayanamsha: str = "Lahiri", tz: str = "UTC") -> List[Tuple[date, str]]:
    """All 12 sidereal Sankrantis for the given Gregorian year. Cached."""
    return list(_sankrantis_for_year_cached(year, ayanamsha, tz))


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


def _scan_pournimas(start: date, end: date, ayanamsha: str = "Lahiri") -> List[Tuple[date, PanchangamDay]]:
    """All Pournima dates in a range, sampled at IST sunrise (Hindu-calendar reference).

    drikpanchang and the Hindu calendar tradition determine festival dates by the
    tithi active at IST sunrise. This function uses Coimbatore (Asia/Kolkata) as
    the reference location for festival-date detection regardless of where the
    user is.
    """
    out = []
    d = start
    while d <= end:
        p = _panchangam_at_india_ref(d, ayanamsha)
        if p.tithi["index"] == 15:
            out.append((d, p))
        d += timedelta(days=1)
    return out


def _scan_amavasyas(start: date, end: date, ayanamsha: str = "Lahiri") -> List[Tuple[date, PanchangamDay]]:
    out = []
    d = start
    while d <= end:
        p = _panchangam_at_india_ref(d, ayanamsha)
        if p.tithi["index"] == 30:
            out.append((d, p))
        d += timedelta(days=1)
    return out


def _panchangam_at_india_ref(d: date, ayanamsha: str = "Lahiri") -> PanchangamDay:
    """Panchangam sampled at IST sunrise (Coimbatore reference). Cached per
    (date, ayanamsha) — `_INDIA_REF` location is a module constant."""
    return _panchangam_india_ref_cached(d.toordinal(), ayanamsha)


@lru_cache(maxsize=4096)
def _panchangam_india_ref_cached(ordinal: int, ayanamsha: str) -> PanchangamDay:
    return panchangam_for_date(date.fromordinal(ordinal), _INDIA_REF, ayanamsha)


def _tithi_active_during_day(d: date, target_tithi: int, ayanamsha: str = "Lahiri") -> bool:
    """Check if the target tithi was active at IST sunrise of either d or d-1.

    Festivals like Mahashivaratri use the rule "tithi spans the night" (Nishita
    rule). Sampling at a single sunrise can miss the tithi entirely if it falls
    between two sunrises. This helper checks both d and d-1 IST sunrise.
    """
    p_today = _panchangam_at_india_ref(d, ayanamsha)
    if p_today.tithi["index"] == target_tithi:
        return True
    p_yest = _panchangam_at_india_ref(d - timedelta(days=1), ayanamsha)
    if p_yest.tithi["index"] == target_tithi:
        return True
    return False


@lru_cache(maxsize=512)
def find_mahashivaratri(year: int, loc_name: Optional[str] = None, ayanamsha: str = "Lahiri") -> Optional[date]:
    """Phalguna Krishna Chaturdashi (T29) — Nishita-spanning rule.

    Classical rule: Mahashivaratri is observed on the day d when T29 (Krishna
    Chaturdashi) spans Nishita (~midnight of d, in IST). drikpanchang uses
    this rule, which is why Mahashivaratri is published as the day BEFORE
    T29 appears at IST sunrise — T29 spans the preceding night.

    Detection: scan for the day d where the next IST sunrise (d+1) sees T29
    active. That means T29 was active during d's night, including Nishita.
    The Sun-in-Kumbha (sidereal 300-330°) constraint disambiguates from any
    other T29 in the year.

    Verified against drikpanchang 2024-2028 to ±1 day (boundary years where
    T29 starts very close to midnight may differ by 1 day across sources).
    """
    d = date(year, 1, 25)
    end = date(year, 3, 31)
    while d <= end:
        p_next = _panchangam_at_india_ref(d + timedelta(days=1), ayanamsha)
        if p_next.tithi["index"] == 29:
            sun_lon = sidereal_sun_longitude(d, _INDIA_REF, ayanamsha)
            if 300.0 <= sun_lon < 330.0:
                return d
        d += timedelta(days=1)
    return None


@lru_cache(maxsize=512)
def find_guru_pournima(year: int, loc_name: Optional[str] = None, ayanamsha: str = "Lahiri") -> Optional[date]:
    """Ashadha Pournima — the Pournima following an Amavasya in sidereal Mithuna.

    Ashadha lunar month (Amanta convention) starts after the Amavasya occurring
    while Sun is in Mithuna (Gemini, sidereal 60-90°). Guru Pournima is the
    Pournima within that lunar month. This anchor is robust to year-edge cases
    where Moon at Ashadha Pournima is in Mula (just before Purva Ashadha) or
    Shravana (just after Uttara Ashadha) — e.g. 2028.

    Per Isha 'Story of Guru Purnima': "On the first full moon after the summer
    solstice, [Adiyogi] decided to teach." Verified against drikpanchang
    2024-2028.
    """
    amavs = _scan_amavasyas(date(year, 5, 25), date(year, 7, 25), ayanamsha)
    mithuna_amavs = []
    for d, _ in amavs:
        sun_lon = sidereal_sun_longitude(d, _INDIA_REF, ayanamsha)
        if 60.0 <= sun_lon < 90.0:
            mithuna_amavs.append(d)
    if not mithuna_amavs:
        return None
    am = mithuna_amavs[-1]
    pms = _scan_pournimas(am + timedelta(days=10), am + timedelta(days=20), ayanamsha)
    return pms[0][0] if pms else None


@lru_cache(maxsize=512)
def find_buddha_pournima(year: int, loc_name: Optional[str] = None, ayanamsha: str = "Lahiri") -> Optional[date]:
    """Vaishakha Pournima — the Pournima following an Amavasya in sidereal Mesha.

    Vaishakha lunar month (Amanta convention) starts after the Amavasya that
    occurs while Sun is in Mesha (Aries). Buddha Pournima is the Pournima
    within that lunar month. This is more robust than 'first Pournima with Sun
    in Mesha', which fails in years (2024, 2027) where Chaitra Pournima also
    has Sun in Mesha — the older rule picked Chaitra Pournima ~30 days too
    early.

    Verified against drikpanchang for 2024-2028.
    """
    amavs = _scan_amavasyas(date(year, 3, 15), date(year, 5, 20), ayanamsha)
    mesha_amavs = []
    for d, _ in amavs:
        sun_lon = sidereal_sun_longitude(d, _INDIA_REF, ayanamsha)
        if 0.0 <= sun_lon < 30.0:
            mesha_amavs.append(d)
    if not mesha_amavs:
        return None
    am = mesha_amavs[-1]
    pms = _scan_pournimas(am + timedelta(days=10), am + timedelta(days=20), ayanamsha)
    return pms[0][0] if pms else None


@lru_cache(maxsize=512)
def find_naga_panchami(year: int, loc_name: Optional[str] = None, ayanamsha: str = "Lahiri") -> Optional[date]:
    """Shravana Shukla Panchami — fifth tithi of the Shukla paksha that begins
    after the Amavasya occurring while Sun is in sidereal Karka (Cancer).

    Shravana lunar month (Amanta) starts after the Amavasya whose Sun is in
    Karka. Naga Panchami is tithi 5 of that month's Shukla paksha. Anchoring
    on the Karka-Amavasya is robust to Adhika Masa (intercalary lunar month)
    edge cases that broke the older "second Shukla Panchami after solstice"
    heuristic.

    Verified against drikpanchang for 2024-2028.
    """
    amavs = _scan_amavasyas(date(year, 6, 25), date(year, 8, 25), ayanamsha)
    karka_amavs = []
    for d, _ in amavs:
        sun_lon = sidereal_sun_longitude(d, _INDIA_REF, ayanamsha)
        if 90.0 <= sun_lon < 120.0:
            karka_amavs.append(d)
    if not karka_amavs:
        return None
    am = karka_amavs[-1]
    d = am + timedelta(days=4)
    end = am + timedelta(days=8)
    while d <= end:
        p = _panchangam_at_india_ref(d, ayanamsha)
        if p.tithi["index"] == 5 and p.paksha == "Shukla":
            return d
        d += timedelta(days=1)
    return None


@lru_cache(maxsize=128)
def margali_window(year: int, loc_name: Optional[str] = None, ayanamsha: str = "Lahiri") -> Tuple[date, date]:
    """Margali masa = Sun in sidereal Dhanu (Sagittarius, rashi 8).

    Per seed talk [00:39:10]: 'Tamil month of Margali starts on 16th December
    towards the end of Dakshinayana ... cold water dip before sunrise at
    Brahma Muhurtam ... do this for a whole mandela or a period of 40 to 48
    days.' Returns (Margali start, Margali start + 48 days mandala end).
    The IST timezone reference is used for the Sankranti boundary.
    """
    start = find_sankranti(year - 1, 8, ayanamsha, "Asia/Kolkata")
    return start, start + timedelta(days=48)


# Backward-compatible signature wrappers for callers that pass a Location.
# Festival dates are global (sampled at IST sunrise), so the location is
# only used for sandhya/sunrise overlap downstream — not for the date itself.
def _norm_loc_arg(arg: Any) -> Optional[str]:
    if arg is None or isinstance(arg, str):
        return arg
    if isinstance(arg, Location):
        return arg.name
    return None


_orig_find_mahashivaratri = find_mahashivaratri
_orig_find_guru_pournima = find_guru_pournima
_orig_find_buddha_pournima = find_buddha_pournima
_orig_find_naga_panchami = find_naga_panchami
_orig_margali_window = margali_window


def find_mahashivaratri(year: int, loc: Any = None, ayanamsha: str = "Lahiri") -> Optional[date]:  # type: ignore[no-redef]
    return _orig_find_mahashivaratri(year, _norm_loc_arg(loc), ayanamsha)


def find_guru_pournima(year: int, loc: Any = None, ayanamsha: str = "Lahiri") -> Optional[date]:  # type: ignore[no-redef]
    return _orig_find_guru_pournima(year, _norm_loc_arg(loc), ayanamsha)


def find_buddha_pournima(year: int, loc: Any = None, ayanamsha: str = "Lahiri") -> Optional[date]:  # type: ignore[no-redef]
    return _orig_find_buddha_pournima(year, _norm_loc_arg(loc), ayanamsha)


def find_naga_panchami(year: int, loc: Any = None, ayanamsha: str = "Lahiri") -> Optional[date]:  # type: ignore[no-redef]
    return _orig_find_naga_panchami(year, _norm_loc_arg(loc), ayanamsha)


def margali_window(year: int, loc: Any = None, ayanamsha: str = "Lahiri") -> Tuple[date, date]:  # type: ignore[no-redef]
    return _orig_margali_window(year, _norm_loc_arg(loc), ayanamsha)


# Keep _find_pournimas as a compatibility alias for any external caller.
_find_pournimas = lambda start, end, loc, ayanamsha="Lahiri": _scan_pournimas(start, end, ayanamsha)


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
            "rule": "Phalguna Krishna Chaturdashi (Nishita-spanning), Sun in sidereal Kumbha",
            "note": "Natural upsurge of energy; spine-vertical all night; |lat|=11° is peak.",
        })

    gpm = find_guru_pournima(d.year, loc, ayanamsha)
    if gpm == d:
        events.append({
            "name": "Guru Pournima",
            "type": "lunar+solar",
            "rule": "Ashadha Pournima — Pournima following an Amavasya in sidereal Mithuna",
            "note": "Adi Yogi turned south to teach; day to earn grace.",
        })

    bpm = find_buddha_pournima(d.year, loc, ayanamsha)
    if bpm == d:
        events.append({
            "name": "Buddha Pournima",
            "type": "lunar+solar",
            "rule": "Vaishakha Pournima — Pournima following an Amavasya in sidereal Mesha",
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
    effect manifests at the given latitude. Hemisphere-symmetric — the
    centrifugal-force claim is by latitude magnitude, not by sign.

    kind = 'mahashivaratri': 1.0 at |lat|=11° (Isha Yoga Center latitude band),
        attenuated by Gaussian with sigma 15° on |lat|. Sadhguru's claim
        (Isha encyclopedia, secondary source): "maximum amount of centrifugal
        force happens at approximately eleven degrees latitude."

    kind = 'equinox_envelope': flat 1.0 inside |lat| in [23, 33]°, 0.6 outside.
        Sadhguru's claim (seed talk [00:23:16]): "particularly between 23 to 33
        degree latitude this effect will be at its highest."
    """
    if kind == "mahashivaratri":
        sigma = 15.0
        return float(exp(-((abs(latitude) - 11.0) ** 2) / (2 * sigma ** 2)))
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

    # Castor oil / wet head between Chitra Pournami and June solstice.
    # Chitra Pournami / Chaitra Pournima = first Pournima after the March
    # equinox (the lunar month name "Chaitra" derives from Chitra nakshatra,
    # but in practice the Pournima Moon may be in adjacent Hasta/Swati;
    # drikpanchang-published Chitra Pournami matches "first Pournima after
    # March equinox" for the years 2024-2028).
    me = find_equinox_solstice(d.year, "March equinox", loc.timezone)
    js = find_equinox_solstice(d.year, "June solstice", loc.timezone)
    chitra_pms = _scan_pournimas(me + timedelta(days=1), me + timedelta(days=32), ayanamsha)
    chitra_pm = chitra_pms[0][0] if chitra_pms else None
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
