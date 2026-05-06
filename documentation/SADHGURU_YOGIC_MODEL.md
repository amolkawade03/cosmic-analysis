# Sadhguru-Faithful Yogic Model — Design Specification

This document is the source-fidelity contract for the yogic extension of
`cosmic_engine.py`. Every feature added in `yogic_engine.py` must trace to
a position Sadhguru has stated. Features that contradict his stated views
are either reframed or removed.

The three source bodies this design draws from:

1. **`transcripts/sadhguru_panchangam_2025.txt`** — the seed talk (360 program).
   Timestamps in this doc reference that talk.
2. **`documentation/SOURCE_KEY_POINTS.md`** — the ten distilled positions
   already adopted as project acceptance criteria.
3. **Sadhguru-authored / Isha-authored material** at sadhguru.org and the
   Sadhguru Encyclopedia. URLs cited inline. Sourcing caveat: a structured
   web-research pass found that direct WebFetch to isha.sadhguru.org is
   blocked (403); quotations below were assembled from search-result
   snippets that recur verbatim across multiple Isha-owned URLs and Isha
   social posts. Where there is any doubt, the quotation is paraphrased
   and the URL is included so a human can verify.

---

## Design philosophy: what Sadhguru's system IS and ISN'T

| The system IS | The system IS NOT |
|---|---|
| Cosmic-geometry observation of *real* astronomical events | Sign-based zodiac prediction |
| Awareness of high-leverage windows | Verdict on whether to act |
| Sadhana-aligned timing | Muhurta-shopping for life events |
| Lunar / solar / equinox / solstice cycles | Vimshottari Dasha, divisional charts |
| Anti-fatalist | Anti-action ("don't do it during Rahu Kala") |
| Microcosm-macrocosm reflection | Per-individual horoscope predictions |

> "It is not about blaming the stars or the planet for everything that you
> do or you do not do."  — [00:13:58]

> "The stars and the planets need not decide your experience of life. You
> and you alone should be the one to decide your inner experience."  —
> [00:41:41]

> "Astrology is an interpretation of astronomy. Whenever you interpret
> something, you invariably miss out on a lot of points. Misinterpretation
> is what is happening."
> — <https://isha.sadhguru.org/en/wisdom/article/does-astrology-work>

> "If any human being's life can be written before he lives it, that is
> for sure a horror-scope."
> — <https://isha.sadhguru.org/en/wisdom/article/horoscopes-or-horror-scopes>

Anything in the model that sounds like a verdict ("avoid", "do not do",
"this is bad for you") or a personal forecast ("you'll get X in Y") is the
bug. The source position is **astronomy, not astrology** — observe the
geometry, bring awareness, decide for yourself.

---

## Twelve features — each grounded in source

### 1. Astronomical solstice for ayana (with sidereal Sankranti as parallel marker)

> "The period from winter solstice in December to summer solstice in June
> is called uttarayana. The northern run of the sun. ... In the yogic
> tradition, uttarayana is seen as a time of harvest. ... Dakshinayana is
> considered a time to work upon yourself."  — [00:37:24]

> "In terms of sadhana, Dakshinayana is for purification. Uttarayana is
> for enlightenment. Particularly, the first half of Uttarayana until the
> equinox in March is a period where the maximum amount of grace is
> available. The human system is more receptive to grace at that time
> than any other."
> — <https://isha.sadhguru.org/en/wisdom/article/significance-uttarayana>

**Behaviour:** `ayana_for_date()` returns Uttarayana from the December
solstice through the June solstice (computed astronomically from the Sun's
**tropical** longitude crossing 270° / 90°). Dakshinayana from June solstice
through December solstice. A separate field `peak_grace_window` is True
during Makar Sankranti (sidereal Sun crosses 0° Capricorn, ~Jan 14)
through the March equinox — Sadhguru's stated peak grace window.

**Why astronomical solstice and not sidereal Sankranti for ayana?** The
seed talk at [00:37:24] is explicit: "winter solstice in December to summer
solstice in June." That is astronomical, not sidereal. He acknowledges
elsewhere [00:21:30] that the sidereal Hindu calendar is "24 days off"
the actual sky — meaning the calendar's labels lag the physical event.
Sadhguru's stated frame is the *physical* event. The sidereal Sankranti
is preserved as a parallel marker (Makar Sankranti / Pongal is named in
the talk and is the start of his peak-grace window) but not as the ayana
boundary.

This is a revision from the earlier design draft, which had used sidereal
Sankranti for ayana. The supplementary research surfaced Sadhguru's own
preference for the observable solstice frame, and the text confirms it.

**Replaces:** the Gregorian month/day cutoffs in `cosmic_engine.ritu_and_ayana`.

---

### 2. Festival / vrata layer — Sadhguru-endorsed only

> "All Indian festivals are calendar oriented not belief oriented based on
> how the sun, moon and earth are aligned."  — [00:35:12]

**Behaviour:** `detect_festivals(date, location)` returns a list of active
or imminent yogic events. Each event has: name, type (lunar / solar /
sandhi), the cosmic-geometry rule that defines it, and a sadhana note in
the language of the source.

**Events implemented (each grounded):**

| Event | Cosmic-geometry rule | Source endorsement |
|---|---|---|
| Pournami | Tithi index = 15 | "If you are seeking wellbeing, Pournami is sacred" — Isha "Difference Between Pournami and Amavasya" |
| Amavasya | Tithi index = 30 | "If you are seeking liberation, Amavasya is sacred" — same URL |
| Ekadashi (each paksha) | Tithi index = 11 (Shukla) or 26 (Krishna) | "Fasting twice a month on Ekadashi days is the best way to do it" — Isha "Ekadashi" article |
| Pradosham | Trayodashi (T13/T28) ±90 min around sunset | NEUTRAL — general Shaiva tradition; NOT a primary Sadhguru emphasis. Surfaced because Sandhya overlap is Sadhguru-endorsed |
| Mahashivaratri | Phalguna Krishna Chaturdashi spanning Nishita, Sun in sidereal Kumbha | Flagship Sadhguru night; "natural upsurge of energy in a human being" — Isha Mahashivratri page |
| Guru Pournima | First Pournami after June solstice | "On the first full moon after the summer solstice, [Adiyogi] decided to teach" — Isha "Story of Guru Purnima" |
| Buddha Pournima | 3rd Pournami after Uttarayana begins (i.e. after Dec solstice; ~ Vaishakha Pournima) | "The third purnima after the earth shifts to the northern run of the sun" — Isha "Buddha Pournami" |
| Naga Panchami | Shukla Panchami in Shravana (Sun in tropical Cancer/Leo, Moon ~Hasta-Chitra) | "Significant for those who want to penetrate and know life beyond their physicality" — Isha "Naga Panchami" |
| Margar Sankranti / Pongal | Sun crosses 0° sidereal Capricorn (Lahiri) | Named in seed talk; "from sadhana pada we are shifting to kaivalya pada" — Isha Pongal article |
| All sidereal Sankrantis | Sun crosses 0° of any rashi | Five-limb calendar context |
| Margali masa | Sun in sidereal Dhanu (Sagittarius), ~Dec 16 → mid-Jan | "Tamil month of Margali starts on 16th December ... cold water dip before sunrise at Brahma Muhurtam ... 40 to 48 day mandala" — [00:39:10] |
| Margali mandala day | Each day in Margali masa | "Doing this process for just one day will only shock the body. ... do this for a whole mandela" — [00:40:00] |
| Spring-equinox new-year window | First new moon / full moon after March equinox | "We have Ugadi in the south, Gudipadwa, Vishu and so many other festivals ... to mark this day of the first new moon day or the full moon day after the spring equinox" — [00:19:56] |

**Events deliberately excluded:**

- Janmashtami, Ram Navami, Diwali, Holi, Karthigai, Vaikuntha Ekadashi
  (regional/devotional festivals not specifically distinguished by
  Sadhguru-grounded geometry).
- Chitra Pournami — supplementary research found NO Sadhguru-specific
  emphasis distinguishing Chitra Pournami from any other Pournami. Kept
  as a generic Pournami in the festival list, NOT as a special event.
  The seed talk's "castor oil from Chitra Pournami till summer solstice"
  point is captured as a *regimen practice* (feature 5), not as a separate
  festival.
- Adi Shankara Jayanti — no Isha emphasis on observing this Jayanti found
  in the supplementary research.

---

### 3. Equinox / solstice run-up awareness (with 11° latitude weighting)

> "I bow down to the equinox because I am made of the equinox. ... I am a
> child of equinox."  — [00:24:39]

> "On equinox, the masculine and feminine influences on the planet are in
> balance — the best day to transcend physical compulsiveness."
> — <https://isha.sadhguru.org/en/wisdom/quotes/date/march-20-2017>

> "Particularly between 23 to 33 degree latitude. ... India is partly in
> this latitude. Some parts of Europe, China and United States are in that
> latitude. ... Maximum amount of development has happened on this planet
> [in this band]."  — [00:23:16]

> "The maximum amount of centrifugal force happens at approximately eleven
> degrees latitude ... so there is a natural upsurge of energy."
> — <https://sadhguru-encyclopedia.org/2021/10/08/11-degrees-eleven-degrees/>

**Behaviour:** `equinox_solstice_proximity(date)` returns:
- The next equinox / solstice (computed from Sun's tropical longitude
  crossing 0° / 90° / 180° / 270°).
- Days until it.
- A "phase" tag: `runup_12d` (within 12 days before), `peak_3d` (within
  3 days either side), `aftermath_12d` (within 12 days after), `quiet`.

`latitude_intensity(latitude)` returns a 0.0-to-1.0 scalar:
- For Mahashivaratri specifically: 1.0 at 11°N, attenuated by Gaussian
  with sigma 15° (so San Jose at 37°N ~ 0.10, Coimbatore at 11°N ~ 1.0,
  Mumbai at 19°N ~ 0.78).
- For equinox effects (magnetic envelope disturbance): the 23-33° band
  carries a different curve — 1.0 inside 23-33°N, 0.6 outside.

These weights modulate the **narrative output**, not the score. The
narrative says "at your latitude this effect is mild / strong"; the
window's score is unaffected.

**12-day window:** The seed talk doesn't specify a precise number. Twelve
days is a documented tunable, not a magic constant — it corresponds to
roughly the lunar fortnight Sadhguru references when discussing Pournami
practices.

---

### 4. Sandhya / Brahma Muhurta as first-class sadhana windows

> "If you are looking for dramatic spiritual progress, you must do your
> yogic practices before sunrise ... starting the practices at the Brahma
> Muhurta, which is the last quarter of the night."
> — <https://isha.sadhguru.org/en/wisdom/article/brahma-muhurta-time-to-create-yourself>

> "Sandhya means — 20 minutes before sunrise, 20 minutes after sunrise.
> Or 20 minutes before sunset, and 20 minutes after sunset."
> — <https://isha.sadhguru.org/en/wisdom/article/best-time-to-practice-yoga>

> "The four times in a day when there's a transitionary period — morning,
> afternoon, evening and midnight."  — [00:33:13]

**Behaviour:** Already present in `cosmic_engine.windows_for_day`. The
extension:

1. **Tightens Sandhya to ±20 minutes** (not ±24) per the explicit
   Sadhguru statement at the Isha "Best time to practice yoga" article.
2. **Adds Madhyahna Sandhya** (true solar noon ±20 min) — the third
   sandhi the seed talk names. Existing Abhijit window is a separate
   classical-Jyotisha concept (different lineage); both are surfaced
   with separate names.
3. **Adds Nishi Sandhya** (midnight ±20 min) — the fourth sandhi.
   Flagged "may not be relevant for a whole lot of people" per the
   seed talk's own caveat.
4. **Brahma Muhurta** stays at "last quarter of the night" computed as
   ~96 to ~48 minutes before sunrise. Sadhguru's Isha article says "the
   last quarter of the night" as the canonical frame; the existing
   96–48 minute window is a reasonable approximation.

---

### 5. Sadhguru-stated regimen items (NOT a generic Ayurveda 6-ritu schema)

> "What you ingest is as important as how you breathe. ... Lakshmi charu in
> Andhra Pradesh, palisadam in Tamil Nadu, kuru in Karnataka ... these
> things are cooling agents, they cool the system and they're very rich in
> B12."  — [00:35:57]

> "From this day onwards [Chitra Pournami] till the summer solstice comes
> ... no farmer went out onto the field or no Tamil person at that time
> went out without applying castor oil."  — [00:34:06]

> "The Tamil month of Margali starts on 16th December towards the end of
> Dakshinayana. Margali is the time to bring stability and balance. ...
> cold water dip before sunrise preferably at the Brahma Muhurtam. ...
> Doing this process for just one day will only shock the body. ... do
> this for a whole mandela or a period of 40 to 48 days."  — [00:39:10]

**Behaviour:** `regimen_for_date(date, location)` returns the specific
practices Sadhguru names in the seed talk for the date's cosmic position.
This is **not** a generic 6-ritu Ayurvedic schema (Ayurveda is a
complementary tradition, not Sadhguru's primary frame).

| Trigger | Practice |
|---|---|
| Date is between Chitra Pournami and June solstice | "Apply castor oil on top of head before going out (or keep top of head wet)" |
| Date is during equinox `peak_3d` or `runup_12d` | "Keep hair / top of head wet, particularly during the four sandhyas" |
| Sun in tropical Cancer / Leo (Grishma months) | "Cooling foods rich in B12 — Lakshmi charu / palisadam / kuru — fresh seasonal" |
| Date is in Margali masa | "Cold water dip before sunrise at Brahma Muhurta — sustain for 40-48 days for a full mandala" |
| Date is Pournami | "Subtle, love-toned upward pull — fasting tradition or sadhana, not heavy work" |
| Date is Amavasya | "Inward, base-toned downward pull — rest, observation, sadhana inward" |
| Date is Ekadashi | "Body's natural fasting day; if prepared, fast — otherwise light food + sadhana" |

If no specific Sadhguru-stated practice applies for a given date, the
regimen returns an empty list. Honest gap-marking, not invented content.

A separate, optional `ritu_charya_ayurveda(ritu)` function exists for
those who want the broader 6-ritu Ayurvedic guidance — it is **labelled
"Ayurveda complement, not a Sadhguru emphasis"** and returned only when
explicitly requested.

---

### 6. Anti-fatalism reframe of scoring

> "It is not about blaming the stars or the planet ... it is about
> enhancing your ability to respond."  — [00:13:58]

> "Planets are inanimate things ... should they decide the course of your
> destiny, or should human nature decide the destiny of inanimate things?
> Human nature should decide."
> — <https://isha.sadhguru.org/en/wisdom/article/horoscopes-or-horror-scopes>

**Behaviour:** Five changes to `cosmic_engine.score_slot`:

1. **Bands renamed.** `Avoid` → `Low Support`. `Caution` → `Variable`.
   The five-band ladder becomes: Strong Support / Supportive / Neutral /
   Variable / Low Support. None are verdicts; all describe alignment.
2. **Negative penalties removed.** Rahu Kala, Yamaganda, Gulika Kala,
   Ashtama Chandra all become **annotations only** — flagged in `notes`,
   not in score. The user sees "Rahu Kala overlap" in explanation and is
   trusted to decide what that means for them.
3. **Tara Bala scoring REMOVED entirely.** The supplementary research
   surfaced that Sadhguru does NOT endorse nakshatra-as-personality or
   Tara-Bala-style nakshatra-matching for muhurta selection. Janma
   Nakshatra remains visible as descriptive birth data (the seed talk
   names nakshatra as a panchangam limb), but it does not score windows.
4. **Chandra Bala kept but reduced** — only as a positive +6 bonus when
   supportive (count in {1, 3, 6, 7, 10, 11}). The "not supportive"
   penalty and Ashtama Chandra penalty are both removed. Chandra Bala
   measures Moon's transit relative to natal Moon — gravitational/lunar
   alignment, which Sadhguru does endorse as a real influence
   ("the basis of your madness ... it's an empowerment").
5. **Score becomes additive-positive only.** Base 0; sum of supportive
   contributions present. The score literally measures alignment
   strength, not net judgement. Maximum theoretical score is bounded by
   the sum of possible bonuses (~50), and bands re-calibrate against
   that ceiling.

---

### 7. Daily alignment text — the Kala → awareness chain

> "Until you have reached that state of liberation, until you transcend
> the cycles of time and space, you must learn to ride the cycles. To
> ride the cycles, you need the right kind of calendar."  — [00:43:51]

**Behaviour:** `daily_yogic_alignment(date, location, panchangam,
festivals, state)` produces a six-line narrative walking:

1. **Kala** — what time-frame this day sits in (ayana, lunar phase,
   distance to next equinox/solstice).
2. **Geometry** — the day's cosmic configuration in plain language.
3. **Environment** — environmental notes (equinox proximity, latitude
   intensity, Margali mandala day, etc.).
4. **Body** — Sadhguru-stated regimen item if one applies; otherwise
   neutral note.
5. **Mind** — Moon's lunar phase intensity ("Pournami = upward, love
   toned" / "Amavasya = inward, base toned" / etc.).
6. **Awareness** — the source's terminal pointer ("You and you alone
   should be the one to decide your inner experience" — [00:41:41]).

The existing `daily_alignment_text` returns five static keys. The new
function interpolates real values; the static `principle` line is
preserved as the closing pointer.

---

### 8. Inner-state input (narrative, not score)

> "The human system is a microcosm of the larger cosmos."  — [00:09:26]

**Behaviour:** Optional `YogicState` dataclass — sleep_quality
(low/normal/high), agitation (low/normal/high), intention (sadhana /
harvest / rest), recent_practices (list of strings such as "Shambhavi",
"Surya Kriya"). When provided, it does **not** alter scores. It alters
the narrative output — e.g., if agitation is high, the body line
emphasizes pranayama; if intention is harvest, the alignment line
emphasizes Uttarayana / Abhijit windows.

---

### 9. Lunar-phase intensity ladder

> "If you are seeking wellbeing, Pournami is sacred; if you are seeking
> liberation, Amavasya is sacred. ... Pournami nights have a more subdued
> quality which is more subtle, pleasant and beautiful — more like love
> ... Amavasya being more sex-oriented and Pournami more love-oriented."
> — Isha "Difference Between Pournami and Amavasya"

**Behaviour:** `lunar_intensity(date)` returns one of:
- `pournami` (full moon, Tithi 15 ±1 day) — "wellbeing, love, upward"
- `amavasya` (new moon, Tithi 30 ±1 day) — "liberation, base, inward"
- `ekadashi` (Tithi 11 or 26) — "natural fasting day"
- `chaturdashi` (Tithi 14 or 29) — "preparation day before Pournami /
  Amavasya"
- `waxing_active` (Shukla Tithi 1-10, 12-13)
- `waning_quiet` (Krishna Tithi 1-10, 12-13)

The narrative output uses this to set the day's energy posture.

---

### 10. Variable-length day-hora and night-hora

The seed talk doesn't specifically address hora computation, but the
existing fixed-60-minute slabs in `cosmic_engine.hora_lord` are a known
defect (COUNCIL_REVIEW.md flaw #5).

**Behaviour:** `hora_lord_variable(slot_start, sunrise, sunset)` divides
day = (sunrise → sunset) into 12 equal day-horas, night = (sunset →
next_sunrise) into 12 equal night-horas. Day-horas start with the vara
lord. Night-horas start with the 5th lord forward in the planetary order
(standard Jyotisha rule).

**Source-fidelity caveat:** Hora-of-the-hour is a classical Jyotish
device. Sadhguru does not specifically emphasize it. It's preserved
because (a) it was in the original engine, (b) it gates the existing
"Sadhana / meditation" hora bonus that maps onto Sadhguru-aligned
Jupiter / Sun / Moon hours. If the source-fidelity council deems hora
non-Sadhguru, it can be retired in v2.

---

### 11. Mahashivaratri night plan (latitude-weighted)

> "On this night, the northern hemisphere of the planet is positioned in
> such a way that there is a natural upsurge of energy in a human being.
> ... The maximum amount of centrifugal force happens at approximately
> eleven degrees latitude ... so there is a natural upsurge of energy."
> — Isha Mahashivratri page; sadhguru-encyclopedia.org

**Behaviour:** `mahashivaratri_plan(year, location)` returns:
- The Mahashivaratri date for the year (Krishna Chaturdashi when Sun is
  in tropical Aquarius — typically Feb-March).
- The four "praharas" of the night (sunset → next sunrise, divided into
  four equal segments).
- Brahma Muhurta the next morning.
- A latitude-intensity scalar (1.0 at 11°N, attenuated outward).
- A note on whether to keep spine vertical all night per Sadhguru's
  prescription.

This is the ONE event in the entire model where a specific personal
prescription appears, because Sadhguru is unusually specific about the
practice for it.

---

### 12. Yogic-mode runner

`run_yogic_analysis.py` is the user-facing entry point. Accepts birth
data + location + date range, produces:

- **Day**: panchangam + festivals + alignment narrative + sadhana windows
- **Week**: festival markers + equinox proximity + lunar phase ladder
- **Month**: festival calendar + Margali / Magha / Ashada blocks +
  Sankranti dates
- **Year**: ayana boundaries + 12 Sankrantis + 4 equinox/solstices +
  Mahashivaratri + Guru Pournima + Buddha Pournima + 24 Ekadashis

Replaces the ad-hoc `/tmp/cosmic-run/run_analysis.py` from previous
sessions.

---

## What is explicitly NOT in this model

| Excluded | Why |
|---|---|
| Tara Bala scoring (nakshatra-matching for muhurta) | Sadhguru doesn't endorse nakshatra-as-predictor; "horror-scope" critique |
| Vimshottari Mahadasha / Antardasha predictions | Predictive astrology — Sadhguru rejects |
| Divisional charts (D7, D9, D10, D12) | Predictive astrology — rejected |
| Doshas as fatalistic constraints (Manglik, Sade Sati) | Sadhguru has spoken against fatalistic dosha interpretation |
| Muhurta-shopping for marriage / kid / surgery dates | Source: "respond, not react" — calendar is awareness, not winning-date |
| Personal predictions of career / visa / kids / finances | Sadhguru does not endorse forecast |
| Negative penalties for Rahu Kala / Yamaganda / Ashtama Chandra | Source explicitly rejects this fatalism — [00:13:58], "horror-scopes" article |
| Mercury / Mars / Saturn retrograde caution | Predictive astrology — rejected |
| Sign-based Western tropical zodiac framing | Source uses observable astronomical events, not sign psychology |
| Graha → Pancha Bhuta mapping (Mars=fire, Mercury=earth, etc.) | Sadhguru's Pancha Bhuta is body/cosmos, not graha-element |
| Generic 6-ritu Ayurvedic diet schema as Sadhguru position | Ayurveda is complementary tradition; only seed-talk-specified items are Sadhguru-faithful |

A model that adds these features can be built — it would be a different
project, grounded in classical Jyotish or Ayurvedic lineage, not in
Sadhguru's specific yogic perspective. This file documents the boundary.

---

## Test plan

Each implemented feature has at least one test that anchors it to a known
ground-truth date. Notable anchors:

- **Solstice / Equinox 2026 dates** (astronomical):
  - March equinox: 2026-03-20
  - June solstice: 2026-06-21
  - September equinox: 2026-09-23
  - December solstice: 2026-12-21
- **Sankranti 2026 dates** (sidereal Lahiri):
  - Makara Sankranti: ~2026-01-14
  - Karka Sankranti: ~2026-07-16
- **Mahashivaratri 2026**: 2026-02-15 (Krishna Chaturdashi, Sun in
  tropical Aquarius)
- **Guru Pournima 2026**: 2026-07-29 (Ashadha Pournima — Pournima following
  the Amavasya in sidereal Mithuna)
- **Buddha Pournima 2026**: 2026-05-01 (Vaishakha Pournima — Pournima
  following the Amavasya in sidereal Mesha)
- **Naga Panchami 2026**: Shukla Panchami in Shravana masa
  (Jul-Aug 2026)
- **Anti-fatalism gate**: a Mahashivaratri at sunset with overlapping
  Rahu Kala must NOT produce a `Low Support` band lower than a quiet
  Friday afternoon. The band labels are positive-additive only.
- **Source-fidelity gate**: removing Tara Bala from scoring must not
  break personal-chart visibility (Janma Nakshatra still appears in
  birth-chart output, just not in window scoring).

---

## Source-fidelity gate

The single test that determines whether the extension stays Sadhguru-faithful
is this: **read the day's narrative output to a yogic practitioner who has
listened to the source talk and read Isha's published material. Would they
recognize it as the same dialect?**

If the output sounds like fortune-telling, the model has drifted. If it
sounds like awareness practice grounded in observable astronomy, it's on
track.

`COUNCIL_REVIEW_V2.md` will test this and other gates against the
implementation.
