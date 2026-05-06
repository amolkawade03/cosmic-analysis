from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from math import acos, asin, atan, cos, degrees, floor, radians, sin, tan
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import swisseph as swe

AYANAMSHA = {"Lahiri": swe.SIDM_LAHIRI, "Raman": swe.SIDM_RAMAN, "Krishnamurti": swe.SIDM_KRISHNAMURTI}
VARA_LORD = {"Sunday":"Sun","Monday":"Moon","Tuesday":"Mars","Wednesday":"Mercury","Thursday":"Jupiter","Friday":"Venus","Saturday":"Saturn"}
RASHIS = ["Mesha/Aries","Vrishabha/Taurus","Mithuna/Gemini","Karka/Cancer","Simha/Leo","Kanya/Virgo","Tula/Libra","Vrischika/Scorpio","Dhanu/Sagittarius","Makara/Capricorn","Kumbha/Aquarius","Meena/Pisces"]
NAKSHATRAS = ["Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra","Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]
NAK_LORDS = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"] * 3
YOGAS = ["Vishkambha","Priti","Ayushman","Saubhagya","Shobhana","Atiganda","Sukarma","Dhriti","Shula","Ganda","Vriddhi","Dhruva","Vyaghata","Harshana","Vajra","Siddhi","Vyatipata","Variyan","Parigha","Shiva","Siddha","Sadhya","Shubha","Shukla","Brahma","Indra","Vaidhriti"]
KARANAS = ["Bava","Balava","Kaulava","Taitila","Gara","Vanija","Vishti/Bhadra"]
PLANETS = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE}
HORA_ORDER = ["Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars"]
BENEFIC_TARAS = {0, 2, 4, 6, 8}
BENEFIC_CHANDRA = {1, 3, 6, 7, 10, 11}


@dataclass
class Location:
    name: str
    latitude: float
    longitude: float
    timezone: str

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError(f"Location.latitude must be in [-90, 90], got {self.latitude}")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError(f"Location.longitude must be in [-180, 180], got {self.longitude}")
        try:
            ZoneInfo(self.timezone)
        except Exception as exc:
            raise ValueError(f"Location.timezone is not a valid IANA tz: {self.timezone!r}") from exc


@dataclass
class BirthInput:
    date: date
    time: time
    location: Location
    ayanamsha: str = "Lahiri"

    def __post_init__(self) -> None:
        if self.ayanamsha not in AYANAMSHA:
            raise ValueError(f"BirthInput.ayanamsha must be one of {set(AYANAMSHA)}, got {self.ayanamsha!r}")
        if self.date.year < 1800 or self.date.year > 2400:
            raise ValueError(f"BirthInput.date.year must be in [1800, 2400] for swisseph accuracy, got {self.date.year}")


@dataclass
class PanchangamDay:
    date: str
    location: Dict[str, Any]
    sunrise: str
    sunset: str
    vara: str
    tithi: Dict[str, Any]
    paksha: str
    nakshatra: Dict[str, Any]
    yoga: Dict[str, Any]
    karana: Dict[str, Any]
    sun_rashi: str
    moon_rashi: str
    ayana: str
    ritu: str
    special_windows: List[Dict[str, str]]


def normalize(x: float) -> float:
    return x % 360.0


def to_jd_utc(dt: datetime) -> float:
    utc = dt.astimezone(ZoneInfo("UTC"))
    return swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute / 60 + utc.second / 3600)


def sidereal_lon(jd: float, body: int, ayanamsha: str = "Lahiri") -> float:
    swe.set_sid_mode(AYANAMSHA.get(ayanamsha, swe.SIDM_LAHIRI))
    return normalize(swe.calc_ut(jd, body, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0])


def rashi(lon: float) -> str:
    return RASHIS[int(lon // 30)]


import warnings as _warnings


def noaa_sunrise_sunset(d: date, loc: Location, zenith: float = 90.833) -> Tuple[datetime, datetime]:
    """Civil sunrise/sunset approximation, accurate to ~1-3 minutes at temperate
    latitudes. Replace with swe.rise_trans for stricter almanac work.

    Polar latitudes (|lat| > ~66.5°) on midnight-sun / polar-night dates trigger
    a fallback to 06:00 / 18:00 local time AND emit a UserWarning so callers
    know the output is fictitious. Downstream sandhya / Brahma Muhurta windows
    based on this fallback are not meaningful.
    """
    polar_fallback_used = [False]

    def calc(is_rise: bool) -> datetime:
        n = d.timetuple().tm_yday
        lng_hour = loc.longitude / 15.0
        t = n + ((6 - lng_hour) / 24 if is_rise else (18 - lng_hour) / 24)
        m = (0.9856 * t) - 3.289
        l = normalize(m + 1.916 * sin(radians(m)) + 0.020 * sin(radians(2 * m)) + 282.634)
        ra = degrees(atan(0.91764 * tan(radians(l)))) % 360
        ra = (ra + floor(l / 90) * 90 - floor(ra / 90) * 90) / 15
        sin_dec = 0.39782 * sin(radians(l))
        cos_dec = cos(asin(sin_dec))
        cos_h = (cos(radians(zenith)) - sin_dec * sin(radians(loc.latitude))) / (cos_dec * cos(radians(loc.latitude)))
        if cos_h > 1 or cos_h < -1:
            polar_fallback_used[0] = True
            return datetime.combine(d, time(6 if is_rise else 18), ZoneInfo(loc.timezone))
        h = (360 - degrees(acos(cos_h)) if is_rise else degrees(acos(cos_h))) / 15
        ut = (h + ra - 0.06571 * t - 6.622 - lng_hour) % 24
        local = (datetime.combine(d, time(0), ZoneInfo("UTC")) + timedelta(hours=ut)).astimezone(ZoneInfo(loc.timezone))
        if is_rise and local.date() > d:
            local -= timedelta(days=1)
        if (not is_rise) and local.date() < d:
            local += timedelta(days=1)
        return local
    rise, sett = calc(True), calc(False)
    if polar_fallback_used[0]:
        _warnings.warn(
            f"noaa_sunrise_sunset: polar fallback (|lat|={abs(loc.latitude):.1f}°) at {loc.name} "
            f"on {d.isoformat()} — returned 06:00/18:00 are placeholders, not real sun events. "
            "Downstream sandhya / Brahma Muhurta windows are not meaningful at this lat/date.",
            UserWarning,
            stacklevel=2,
        )
    return rise, sett


def tithi_info(moon: float, sun: float) -> Dict[str, Any]:
    elong = normalize(moon - sun)
    idx = int(elong // 12) + 1
    paksha = "Shukla" if idx <= 15 else "Krishna"
    num = idx if idx <= 15 else idx - 15
    names = ["Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami","Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima/Amavasya"]
    return {"index": idx, "name": names[num - 1], "paksha": paksha, "elongation_degrees": round(elong, 3)}


def nakshatra_info(moon: float) -> Dict[str, Any]:
    span = 360 / 27
    idx = int(moon // span)
    pada = int((moon - idx * span) // (span / 4)) + 1
    return {"index": idx + 1, "name": NAKSHATRAS[idx], "pada": pada, "lord": NAK_LORDS[idx]}


def yoga_info(moon: float, sun: float) -> Dict[str, Any]:
    idx = int(normalize(moon + sun) // (360 / 27))
    return {"index": idx + 1, "name": YOGAS[idx]}


def karana_info(moon: float, sun: float) -> Dict[str, Any]:
    half = int(normalize(moon - sun) // 6) + 1
    if half == 1:
        name = "Kimstughna"
    elif half >= 58:
        name = ["Shakuni", "Chatushpada", "Naga"][(half - 58) % 3]
    else:
        name = KARANAS[(half - 2) % 7]
    return {"index": half, "name": name}


def tropical_sun_longitude(d: date, loc: Location) -> float:
    """Sun's tropical longitude at local noon. Used for astronomical ayana boundaries.

    Per Sadhguru in the seed talk [00:37:24]: 'winter solstice in December to summer
    solstice in June is called uttarayana.' That is the astronomical (tropical) frame.
    """
    noon = datetime.combine(d, time(12, 0), ZoneInfo(loc.timezone))
    jd = to_jd_utc(noon)
    return normalize(swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH)[0][0])


def sidereal_sun_longitude(d: date, loc: Location, ayanamsha: str = "Lahiri") -> float:
    """Sun's sidereal longitude at local noon. Used for Sankranti / rashi labels."""
    noon = datetime.combine(d, time(12, 0), ZoneInfo(loc.timezone))
    jd = to_jd_utc(noon)
    return sidereal_lon(jd, swe.SUN, ayanamsha)


def ritu_and_ayana(d: date, loc: Optional[Location] = None, ayanamsha: str = "Lahiri") -> Tuple[str, str]:
    """Astronomical solstice ayana + sidereal Sankranti ritu.

    Ayana boundary: Sun's tropical longitude crossing 270° (December solstice)
    and 90° (June solstice). Matches Sadhguru's framing in the seed talk
    [00:37:24]: 'winter solstice in December to summer solstice in June is called
    uttarayana.'

    Ritu boundary: Sun's sidereal longitude in 60°-pairs of rashis. Matches the
    traditional Hindu calendar's six-ritu / 12-Sankranti structure named in the
    talk's broader context.
    """
    if loc is None:
        loc = Location("UTC", 0.0, 0.0, "UTC")
    trop = tropical_sun_longitude(d, loc)
    sid = sidereal_sun_longitude(d, loc, ayanamsha)
    ayana = "Uttarayana" if (270 <= trop or trop < 90) else "Dakshinayana"
    rashi_idx = int(sid // 30)
    ritu_table = [
        (0, "Vasanta / Spring"),
        (2, "Grishma / Summer"),
        (4, "Varsha / Monsoon"),
        (6, "Sharad / Autumn"),
        (8, "Hemanta / Early winter"),
        (10, "Shishira / Late winter"),
    ]
    ritu = "Vasanta / Spring"
    for start_rashi, name in ritu_table:
        if start_rashi <= rashi_idx < start_rashi + 2:
            ritu = name
            break
    return ritu, ayana


def windows_for_day(sunrise: datetime, sunset: datetime) -> List[Dict[str, str]]:
    """Daily transition windows.

    Sandhya windows tightened to ±20 minutes per Sadhguru's stated definition
    in the Isha 'Best time to practice yoga' article. Madhyahna Sandhya
    (true noon ±20) added per the seed talk's four-sandhi list [00:33:13].

    Rahu Kala / Yamaganda / Gulika Kala are computed and surfaced as
    informational annotations only — the supplementary research found no
    Sadhguru endorsement of these as 'avoid' windows. Scoring engine no
    longer penalises overlap with them.
    """
    day_len = sunset - sunrise
    segment = day_len / 8
    weekday = sunrise.strftime("%A")
    rahu = {"Monday": 1, "Saturday": 2, "Friday": 3, "Wednesday": 4, "Thursday": 5, "Tuesday": 6, "Sunday": 7}
    yama = {"Sunday": 4, "Monday": 3, "Tuesday": 2, "Wednesday": 1, "Thursday": 0, "Friday": 6, "Saturday": 5}
    gulika = {"Sunday": 6, "Monday": 5, "Tuesday": 4, "Wednesday": 3, "Thursday": 2, "Friday": 1, "Saturday": 0}
    noon = sunrise + day_len / 2
    data = [
        ("Brahma Muhurta", sunrise - timedelta(minutes=96), sunrise - timedelta(minutes=48)),
        ("Sunrise Sandhya", sunrise - timedelta(minutes=20), sunrise + timedelta(minutes=20)),
        ("Madhyahna Sandhya", noon - timedelta(minutes=20), noon + timedelta(minutes=20)),
        ("Abhijit Muhurta", noon - timedelta(minutes=24), noon + timedelta(minutes=24)),
        ("Sunset Sandhya", sunset - timedelta(minutes=20), sunset + timedelta(minutes=20)),
    ]
    for name, mapping in [("Rahu Kala", rahu), ("Yamaganda", yama), ("Gulika Kala", gulika)]:
        n = mapping[weekday]
        data.append((name, sunrise + segment * n, sunrise + segment * (n + 1)))
    return [{"name": n, "start": s.isoformat(), "end": e.isoformat()} for n, s, e in data]


def panchangam_for_date(d: date, loc: Location, ayanamsha: str = "Lahiri") -> PanchangamDay:
    sunrise, sunset = noaa_sunrise_sunset(d, loc)
    jd = to_jd_utc(sunrise)
    moon, sun = sidereal_lon(jd, swe.MOON, ayanamsha), sidereal_lon(jd, swe.SUN, ayanamsha)
    ti, nak = tithi_info(moon, sun), nakshatra_info(moon)
    ritu, ayana = ritu_and_ayana(d, loc, ayanamsha)
    return PanchangamDay(d.isoformat(), asdict(loc), sunrise.isoformat(), sunset.isoformat(), sunrise.strftime("%A"), ti, ti["paksha"], nak, yoga_info(moon, sun), karana_info(moon, sun), rashi(sun), rashi(moon), ayana, ritu, windows_for_day(sunrise, sunset))


def birth_chart(inp: BirthInput) -> Dict[str, Any]:
    dt = datetime.combine(inp.date, inp.time, ZoneInfo(inp.location.timezone))
    jd = to_jd_utc(dt)
    moon = sidereal_lon(jd, swe.MOON, inp.ayanamsha)
    planets: Dict[str, Any] = {}
    for name, body in PLANETS.items():
        lon = sidereal_lon(jd, body, inp.ayanamsha)
        if name == "Rahu":
            planets["Rahu"] = {"longitude": round(lon, 3), "rashi": rashi(lon), "nakshatra": nakshatra_info(lon)}
            ketu = normalize(lon + 180)
            planets["Ketu"] = {"longitude": round(ketu, 3), "rashi": rashi(ketu), "nakshatra": nakshatra_info(ketu)}
        else:
            planets[name] = {"longitude": round(lon, 3), "rashi": rashi(lon), "nakshatra": nakshatra_info(lon)}
    swe.set_sid_mode(AYANAMSHA.get(inp.ayanamsha, swe.SIDM_LAHIRI))
    try:
        _, ascmc = swe.houses_ex(jd, inp.location.latitude, inp.location.longitude, b"W", swe.FLG_SIDEREAL)
        lagna_lon = normalize(ascmc[0])
        lagna = {"longitude": round(lagna_lon, 3), "rashi": rashi(lagna_lon), "rashi_index": int(lagna_lon // 30) + 1}
    except Exception:
        lagna = None
    return {"birth_datetime": dt.isoformat(), "location": asdict(inp.location), "janma_nakshatra": nakshatra_info(moon), "janma_rashi": rashi(moon), "janma_rashi_index": int(moon // 30) + 1, "lagna": lagna, "planets": planets}


# `friction_windows` annotates which windows historically appear in classical
# muhurta as "avoid" — but in this engine they are NEVER penalised. They are
# surfaced as `notes` on overlapping slots so the user can bring awareness, per
# Sadhguru's stated stance ("respond, not react", seed talk [00:13:58]). The
# old `avoid_windows` key was deprecated to remove fatalist semantics from the
# canonical profile dict.
ACTIVITY_PROFILES = {
    "Sadhana / meditation": {"prefer_windows": ["Brahma Muhurta", "Sunrise Sandhya", "Sunset Sandhya", "Madhyahna Sandhya"], "friction_windows": [], "boost_nak": ["Pushya", "Hasta", "Revati", "Shravana", "Anuradha"], "weight_personal": 1.0},
    "Deep work / study": {"prefer_windows": ["Abhijit Muhurta"], "friction_windows": ["Rahu Kala", "Yamaganda"], "boost_nak": ["Rohini", "Mrigashirsha", "Hasta", "Shravana", "Revati"], "weight_personal": 0.8},
    "Investment / finance": {"prefer_windows": ["Abhijit Muhurta"], "friction_windows": ["Rahu Kala", "Yamaganda", "Gulika Kala"], "boost_nak": ["Rohini", "Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada", "Revati"], "weight_personal": 1.2},
    "Travel": {"prefer_windows": [], "friction_windows": ["Rahu Kala", "Yamaganda"], "boost_nak": ["Ashwini", "Mrigashirsha", "Punarvasu", "Hasta", "Anuradha", "Revati"], "weight_personal": 1.0},
    "Ceremony / auspicious start": {"prefer_windows": ["Abhijit Muhurta"], "friction_windows": ["Rahu Kala", "Yamaganda", "Gulika Kala"], "boost_nak": ["Rohini", "Mrigashirsha", "Uttara Phalguni", "Hasta", "Swati", "Anuradha", "Revati"], "weight_personal": 1.4},
    "Health / body reset": {"prefer_windows": ["Brahma Muhurta", "Sunrise Sandhya"], "friction_windows": [], "boost_nak": ["Ashwini", "Pushya", "Hasta", "Shravana"], "weight_personal": 0.8},
}


def tara_bala(day_nak_idx: int, janma_nak_idx: int) -> Dict[str, Any]:
    count = (day_nak_idx - janma_nak_idx) % 27 + 1
    rem = count % 9
    return {"count": count, "remainder": rem, "supportive": rem in BENEFIC_TARAS}


def chandra_bala(day_moon_rashi_idx: int, janma_rashi_idx: int) -> Dict[str, Any]:
    count = (day_moon_rashi_idx - janma_rashi_idx) % 12 + 1
    return {"count_from_janma_rashi": count, "supportive": count in BENEFIC_CHANDRA, "ashtama_chandra": count == 8}


def hora_lord(slot_start: datetime, sunrise: datetime) -> str:
    """Fixed 60-minute hora (legacy). Prefer hora_lord_variable() for accuracy."""
    start = HORA_ORDER.index(VARA_LORD[sunrise.strftime("%A")])
    hour_num = max(0, int((slot_start - sunrise).total_seconds() // 3600))
    return HORA_ORDER[(start + hour_num) % 7]


def hora_lord_variable(slot_start: datetime, sunrise: datetime, sunset: datetime) -> str:
    """Variable-length day-hora and night-hora.

    Day = sunrise to sunset, divided into 12 day-horas. Day-horas start with
    the vara lord. Night = sunset to next sunrise, divided into 12 night-horas;
    night-horas start with the 5th lord forward in HORA_ORDER from the vara
    lord (standard Jyotisha rule).
    """
    if slot_start < sunrise:
        prev_sunset = sunset - timedelta(days=1)
        prev_vara = (sunrise - timedelta(days=1)).strftime("%A")
        night_start_lord = HORA_ORDER[(HORA_ORDER.index(VARA_LORD[prev_vara]) + 4) % 7]
        night_len = (sunrise - prev_sunset).total_seconds()
        idx = int((slot_start - prev_sunset).total_seconds() / (night_len / 12))
        return HORA_ORDER[(HORA_ORDER.index(night_start_lord) + idx) % 7]
    if sunrise <= slot_start < sunset:
        day_len = (sunset - sunrise).total_seconds()
        idx = int((slot_start - sunrise).total_seconds() / (day_len / 12))
        day_start_lord = VARA_LORD[sunrise.strftime("%A")]
        return HORA_ORDER[(HORA_ORDER.index(day_start_lord) + idx) % 7]
    next_sunrise = sunrise + timedelta(days=1)
    night_len = (next_sunrise - sunset).total_seconds()
    idx = int((slot_start - sunset).total_seconds() / (night_len / 12))
    night_start_lord = HORA_ORDER[(HORA_ORDER.index(VARA_LORD[sunrise.strftime("%A")]) + 4) % 7]
    return HORA_ORDER[(HORA_ORDER.index(night_start_lord) + idx) % 7]


def window_overlap(slot_s: datetime, slot_e: datetime, windows: List[Dict[str, str]]) -> List[str]:
    names = []
    for w in windows:
        s, e = datetime.fromisoformat(w["start"]), datetime.fromisoformat(w["end"])
        if max(slot_s, s) < min(slot_e, e):
            names.append(w["name"])
    return names


# Friction windows: surfaced as informational annotations only, never penalised.
# The supplementary research found no Sadhguru endorsement of these as "avoid"
# windows; the seed talk explicitly criticises that fatalism at [00:13:58].
FRICTION_WINDOWS = {"Rahu Kala", "Yamaganda", "Gulika Kala"}


def score_slot(day: PanchangamDay, slot_start: datetime, minutes: int, activity: str, birth: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Positive-additive alignment score (anti-fatalist).

    Score = sum of supportive contributions present in the window. There are
    no negative penalties; flags for Rahu Kala / Yamaganda / Gulika Kala /
    Ashtama Chandra are surfaced in 'notes' only. Tara Bala (nakshatra
    matching) is excluded from scoring per Sadhguru's stated rejection of
    nakshatra-as-predictor; Janma Nakshatra remains visible in the birth
    chart output. Chandra Bala (Moon's transit relative to natal Moon) is
    kept as a positive bonus only — Sadhguru endorses lunar gravity's
    influence on the human system.

    The five-band ladder is now: Strong Support / Supportive / Neutral /
    Variable / Low Support. None are verdicts; all describe alignment.
    """
    profile = ACTIVITY_PROFILES.get(activity, ACTIVITY_PROFILES["Sadhana / meditation"])
    score, reasons, notes = 0.0, [], []
    slot_end = slot_start + timedelta(minutes=minutes)
    overlaps = window_overlap(slot_start, slot_end, day.special_windows)
    for w in overlaps:
        if w in profile["prefer_windows"]:
            score += 12; reasons.append(f"Overlaps {w}")
        if w in FRICTION_WINDOWS:
            notes.append(f"Overlaps {w} (friction window — awareness, not avoidance)")
    if day.nakshatra["name"] in profile["boost_nak"]:
        score += 8; reasons.append(f"Aligned nakshatra: {day.nakshatra['name']}")
    sunrise_dt = datetime.fromisoformat(day.sunrise)
    sunset_dt = datetime.fromisoformat(day.sunset)
    h = hora_lord_variable(slot_start, sunrise_dt, sunset_dt)
    if activity == "Investment / finance" and h in {"Jupiter", "Venus", "Mercury"}:
        score += 6; reasons.append(f"Aligned hora: {h}")
    if activity == "Deep work / study" and h in {"Mercury", "Jupiter", "Sun"}:
        score += 6; reasons.append(f"Aligned hora: {h}")
    if activity == "Sadhana / meditation" and h in {"Jupiter", "Moon", "Sun"}:
        score += 6; reasons.append(f"Aligned hora: {h}")
    personal: Dict[str, Any] = {}
    if birth:
        cb = chandra_bala(RASHIS.index(day.moon_rashi) + 1, birth["janma_rashi_index"])
        tb = tara_bala(day.nakshatra["index"], birth["janma_nakshatra"]["index"])
        personal = {"chandra_bala": cb, "tara_bala": tb}
        if cb["supportive"]:
            score += 6; reasons.append("Chandra Bala aligned")
        if cb["ashtama_chandra"]:
            notes.append("Ashtama Chandra (Moon 8th from natal — informational, not a verdict)")
    score = max(0.0, min(50.0, round(score, 1)))
    if score >= 32:
        band = "Strong Support"
    elif score >= 22:
        band = "Supportive"
    elif score >= 12:
        band = "Neutral"
    elif score > 0:
        band = "Variable"
    else:
        band = "Low Support"
    return {
        "start": slot_start.isoformat(),
        "end": slot_end.isoformat(),
        "score": score,
        "band": band,
        "hora_lord": h,
        "overlaps": overlaps,
        "reasons": reasons[:8],
        "notes": notes[:8],
        "cautions": [],  # preserved for backward compat with tests; new code uses "notes"
        "personal": personal,
    }


def rank_muhurta_windows(d: date, loc: Location, activity: str, birth: Optional[Dict[str, Any]] = None, ayanamsha: str = "Lahiri", slot_minutes: int = 30, top_n: int = 12) -> Dict[str, Any]:
    day = panchangam_for_date(d, loc, ayanamsha)
    sunrise, sunset = datetime.fromisoformat(day.sunrise), datetime.fromisoformat(day.sunset)
    slots, t = [], sunrise
    while t + timedelta(minutes=slot_minutes) <= sunset:
        slots.append(score_slot(day, t, slot_minutes, activity, birth))
        t += timedelta(minutes=slot_minutes)
    slots.sort(key=lambda x: x["score"], reverse=True)
    return {"day": asdict(day), "activity": activity, "top_windows": slots[:top_n], "all_windows": slots}


def daily_alignment_text(day: PanchangamDay) -> Dict[str, str]:
    return {
        "principle": "Use the calendar as a geometry-map for responsiveness, not fatalism.",
        "body": f"{day.ritu}: adjust food, sleep, heat/cold exposure, and workload to the season.",
        "mind": f"Moon in {day.nakshatra['name']} / {day.moon_rashi}: observe the mind before major reactions.",
        "action": f"Vara is {day.vara}; tithi is {day.paksha} {day.tithi['name']}. Prefer aligned action over force.",
        "sadhana": "Brahma Muhurta and Sandhya windows are highlighted for stillness, mantra, pranayama, or meditation.",
    }
