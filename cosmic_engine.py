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


@dataclass
class BirthInput:
    date: date
    time: time
    location: Location
    ayanamsha: str = "Lahiri"


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


def noaa_sunrise_sunset(d: date, loc: Location, zenith: float = 90.833) -> Tuple[datetime, datetime]:
    """Civil sunrise/sunset approximation. Replace with swe.rise_trans for stricter almanac work."""
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
            return datetime.combine(d, time(6 if is_rise else 18), ZoneInfo(loc.timezone))
        h = (360 - degrees(acos(cos_h)) if is_rise else degrees(acos(cos_h))) / 15
        ut = (h + ra - 0.06571 * t - 6.622 - lng_hour) % 24
        local = (datetime.combine(d, time(0), ZoneInfo("UTC")) + timedelta(hours=ut)).astimezone(ZoneInfo(loc.timezone))
        if is_rise and local.date() > d:
            local -= timedelta(days=1)
        if (not is_rise) and local.date() < d:
            local += timedelta(days=1)
        return local
    return calc(True), calc(False)


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


def ritu_and_ayana(d: date) -> Tuple[str, str]:
    md = d.month * 100 + d.day
    ayana = "Uttarayana" if 1222 <= md or md < 621 else "Dakshinayana"
    if 315 <= md < 515:
        ritu = "Vasanta / Spring"
    elif 515 <= md < 715:
        ritu = "Grishma / Summer"
    elif 715 <= md < 915:
        ritu = "Varsha / Monsoon"
    elif 915 <= md < 1115:
        ritu = "Sharad / Autumn"
    elif 1115 <= md or md < 115:
        ritu = "Hemanta / Early winter"
    else:
        ritu = "Shishira / Late winter"
    return ritu, ayana


def windows_for_day(sunrise: datetime, sunset: datetime) -> List[Dict[str, str]]:
    day_len = sunset - sunrise
    segment = day_len / 8
    weekday = sunrise.strftime("%A")
    rahu = {"Monday": 1, "Saturday": 2, "Friday": 3, "Wednesday": 4, "Thursday": 5, "Tuesday": 6, "Sunday": 7}
    yama = {"Sunday": 4, "Monday": 3, "Tuesday": 2, "Wednesday": 1, "Thursday": 0, "Friday": 6, "Saturday": 5}
    gulika = {"Sunday": 6, "Monday": 5, "Tuesday": 4, "Wednesday": 3, "Thursday": 2, "Friday": 1, "Saturday": 0}
    noon = sunrise + day_len / 2
    data = [
        ("Brahma Muhurta", sunrise - timedelta(minutes=96), sunrise - timedelta(minutes=48)),
        ("Sunrise Sandhya", sunrise - timedelta(minutes=24), sunrise + timedelta(minutes=24)),
        ("Abhijit Muhurta", noon - timedelta(minutes=24), noon + timedelta(minutes=24)),
        ("Sunset Sandhya", sunset - timedelta(minutes=24), sunset + timedelta(minutes=24)),
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
    ritu, ayana = ritu_and_ayana(d)
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


ACTIVITY_PROFILES = {
    "Sadhana / meditation": {"prefer_windows": ["Brahma Muhurta", "Sunrise Sandhya", "Sunset Sandhya"], "avoid_windows": [], "boost_nak": ["Pushya", "Hasta", "Revati", "Shravana", "Anuradha"], "weight_personal": 1.0},
    "Deep work / study": {"prefer_windows": ["Abhijit Muhurta"], "avoid_windows": ["Rahu Kala", "Yamaganda"], "boost_nak": ["Rohini", "Mrigashirsha", "Hasta", "Shravana", "Revati"], "weight_personal": 0.8},
    "Investment / finance": {"prefer_windows": ["Abhijit Muhurta"], "avoid_windows": ["Rahu Kala", "Yamaganda", "Gulika Kala"], "boost_nak": ["Rohini", "Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada", "Revati"], "weight_personal": 1.2},
    "Travel": {"prefer_windows": [], "avoid_windows": ["Rahu Kala", "Yamaganda"], "boost_nak": ["Ashwini", "Mrigashirsha", "Punarvasu", "Hasta", "Anuradha", "Revati"], "weight_personal": 1.0},
    "Ceremony / auspicious start": {"prefer_windows": ["Abhijit Muhurta"], "avoid_windows": ["Rahu Kala", "Yamaganda", "Gulika Kala"], "boost_nak": ["Rohini", "Mrigashirsha", "Uttara Phalguni", "Hasta", "Swati", "Anuradha", "Revati"], "weight_personal": 1.4},
    "Health / body reset": {"prefer_windows": ["Brahma Muhurta", "Sunrise Sandhya"], "avoid_windows": [], "boost_nak": ["Ashwini", "Pushya", "Hasta", "Shravana"], "weight_personal": 0.8},
}


def tara_bala(day_nak_idx: int, janma_nak_idx: int) -> Dict[str, Any]:
    count = (day_nak_idx - janma_nak_idx) % 27 + 1
    rem = count % 9
    return {"count": count, "remainder": rem, "supportive": rem in BENEFIC_TARAS}


def chandra_bala(day_moon_rashi_idx: int, janma_rashi_idx: int) -> Dict[str, Any]:
    count = (day_moon_rashi_idx - janma_rashi_idx) % 12 + 1
    return {"count_from_janma_rashi": count, "supportive": count in BENEFIC_CHANDRA, "ashtama_chandra": count == 8}


def hora_lord(slot_start: datetime, sunrise: datetime) -> str:
    start = HORA_ORDER.index(VARA_LORD[sunrise.strftime("%A")])
    hour_num = max(0, int((slot_start - sunrise).total_seconds() // 3600))
    return HORA_ORDER[(start + hour_num) % 7]


def window_overlap(slot_s: datetime, slot_e: datetime, windows: List[Dict[str, str]]) -> List[str]:
    names = []
    for w in windows:
        s, e = datetime.fromisoformat(w["start"]), datetime.fromisoformat(w["end"])
        if max(slot_s, s) < min(slot_e, e):
            names.append(w["name"])
    return names


def score_slot(day: PanchangamDay, slot_start: datetime, minutes: int, activity: str, birth: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    profile = ACTIVITY_PROFILES.get(activity, ACTIVITY_PROFILES["Sadhana / meditation"])
    score, reasons, cautions = 50.0, [], []
    slot_end = slot_start + timedelta(minutes=minutes)
    overlaps = window_overlap(slot_start, slot_end, day.special_windows)
    for w in overlaps:
        if w in profile["prefer_windows"]:
            score += 12; reasons.append(f"Overlaps {w}")
        if w in profile["avoid_windows"]:
            score -= 20; cautions.append(f"Overlaps {w}")
    if day.nakshatra["name"] in profile["boost_nak"]:
        score += 10; reasons.append(f"Supportive nakshatra: {day.nakshatra['name']}")
    h = hora_lord(slot_start, datetime.fromisoformat(day.sunrise))
    if activity == "Investment / finance" and h in {"Jupiter", "Venus", "Mercury"}:
        score += 8; reasons.append(f"Supportive hora: {h}")
    if activity == "Deep work / study" and h in {"Mercury", "Jupiter", "Sun"}:
        score += 8; reasons.append(f"Supportive hora: {h}")
    if activity == "Sadhana / meditation" and h in {"Jupiter", "Moon", "Sun"}:
        score += 6; reasons.append(f"Supportive hora: {h}")
    personal: Dict[str, Any] = {}
    if birth:
        tb = tara_bala(day.nakshatra["index"], birth["janma_nakshatra"]["index"])
        cb = chandra_bala(RASHIS.index(day.moon_rashi) + 1, birth["janma_rashi_index"])
        personal = {"tara_bala": tb, "chandra_bala": cb}
        w = profile["weight_personal"]
        score += (8 if tb["supportive"] else -7) * w
        score += (8 if cb["supportive"] else -8) * w
        if cb["ashtama_chandra"]:
            score -= 12 * w; cautions.append("Ashtama Chandra caution")
        reasons += [x for x in ["Tara Bala supportive" if tb["supportive"] else "", "Chandra Bala supportive" if cb["supportive"] else ""] if x]
        cautions += [x for x in ["Tara Bala not ideal" if not tb["supportive"] else "", "Chandra Bala not ideal" if not cb["supportive"] else ""] if x]
    score = max(0, min(100, round(score, 1)))
    band = "Excellent" if score >= 85 else "Strong" if score >= 72 else "Usable" if score >= 58 else "Caution" if score >= 42 else "Avoid"
    return {"start": slot_start.isoformat(), "end": slot_end.isoformat(), "score": score, "band": band, "hora_lord": h, "overlaps": overlaps, "reasons": reasons[:6], "cautions": cautions[:6], "personal": personal}


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
