# Council of LLM Judges — Review of the Yogic Model

This document records the findings of a four-judge LLM review of the
`cosmic-analysis` project, treating the Sadhguru-inspired material captured in
`PROJECT_ORIGIN.md`, `YOGIC_PERSPECTIVE.md`, and `PERSPECTIVE.md` as the
philosophical source, and comparing it against the rest of `documentation/` and
the implementation in `cosmic_engine.py` / `app.py`.

The full Sadhguru transcript is intentionally not redistributed in this repo
(per `PROJECT_ORIGIN.md`); the review uses the project's own paraphrase of its
yogic premises as the bar.

Four independent judges reviewed in parallel. Each judge had a different lens:

1. Yogic philosophy alignment
2. Astronomical and calculation correctness
3. Software engineering and model design
4. Vedic / Jyotish tradition fidelity

---

## Fundamental flaws (cross-judge consensus)

These items were flagged independently by two or more judges and represent the
deepest problems in the current model.

### 1. The scoring engine contradicts the project's own anti-fatalism stance

`PROJECT_ORIGIN.md` says the tool "should never become fatalistic" and that the
point is to "respond rather than react". `cosmic_engine.py:score_slot`
nevertheless emits a deterministic verdict: base 50, hard-coded ±20 / ±12 / ±8
deltas for window overlaps and bala flags, clipped to [0, 100], and bucketed
into five bands ending in `"Avoid"`. The engine literally produces an `Avoid`
label — the precise posture the origin document forbids.

Flagged by Judges 1 and 3.

### 2. Tropical Gregorian Ayana/Ritu inside an otherwise sidereal pipeline

`cosmic_engine.py:ritu_and_ayana` decides Uttarayana/Dakshinayana and the six
ritus from Gregorian month/day cutoffs (e.g., `1222`, `0621`). Every other
calculation in the engine uses sidereal Lahiri/Raman/Krishnamurti longitudes.
Indian sidereal tradition starts Uttarayana at Makara Sankranti (~Jan 14) and
Dakshinayana at Karka Sankranti (~Jul 14). With Lahiri ayanamsha at ~24°, the
discrepancy is ~24 days and is persistent.

This is a **direct contradiction** of both the source ("equinoxes, solar and
lunar cycles, cosmic geometry") and the engine's own claim of sidereal
calculation. `daily_alignment_text` then surfaces the wrong ritu/ayana to the
user.

Flagged by Judges 1 and 2.

### 3. Three of the five Panchangam limbs are computed but never scored

`documentation/MUHURTA.md` lists Tithi, Nakshatra, Yoga, Karana, Vara, and Hora
as "Universal factors." `cosmic_engine.py:score_slot` only consumes **Nakshatra
and Hora**. Tithi quality (Nanda / Bhadra / Jaya / Rikta / Purna), inauspicious
Yogas (Vyatipata, Vaidhriti, Vyaghata, Parigha, Shula, Ganda, Atiganda, Vajra),
Vishti / Bhadra Karana, and Vara-activity matching are all silently ignored.

A "Ceremony / auspicious start" can score `Excellent` while sitting inside
Bhadra Karana on a Rikta tithi during Vyatipata yoga — the textbook trifecta of
*don't*.

Flagged by Judges 1 (as "Panchangam limbs reduced to a label") and 4 (as
"engine drops three legs of the Panchangam").

### 4. `daily_alignment_text` is a static template, not yogic depth

`cosmic_engine.py:daily_alignment_text` returns a fixed five-key dictionary
with only nakshatra and ritu name interpolation. The Kala → geometry →
environment → body/mind → awareness chain in `YOGIC_PERSPECTIVE.md` is never
walked. This is the one place where the model could carry the yogic frame into
the user experience and instead it emits a stencil.

Flagged by Judges 1 and 3.

### 5. Hora is computed as fixed 60-minute slabs from sunrise

`cosmic_engine.py:hora_lord` divides the day into 60-minute fixed horas. The
Jyotish convention is unequal day-horas of (sunset − sunrise)/12 and
night-horas of (next sunrise − sunset)/12 — equal only at equinox. At
mid-latitude in summer, day-hora is ~75 minutes; the assigned lord drifts off
by one slot well before sunset. The code also does not handle night horas at
all because `rank_muhurta_windows` only iterates sunrise to sunset.

Flagged by Judges 2 and 4.

### 6. Sunrise approximation can flip Tithi / Vara / Nakshatra at boundaries

`cosmic_engine.py:noaa_sunrise_sunset` is a NOAA almanac-style civil
approximation, accurate to ~1–4 minutes at temperate latitudes and degrading
at high latitudes. Tithi, Vara, Nakshatra, Yoga, and Karana are all sampled at
sunrise. When a tithi or nakshatra boundary lies within minutes of sunrise,
the labeled value can flip. `swisseph` already exposes `swe.rise_trans` for
strict almanac sunrise; the docs note this as a future improvement but it is
not surfaced in the UI as a current limitation.

Worse: when `|cos_h| > 1` (polar regions / extreme dates) the function
**silently** returns 06:00 / 18:00 local time. No log, no warning, no UI flag.
The user sees a fabricated sunrise.

Flagged by Judges 2 and 3.

### 7. Personal birth-chart integration is shallow

`README.md` advertises "personal birth-chart integration." In practice the
personalization is Tara Bala + Chandra Bala + Ashtama Chandra + a Whole-Sign
Lagna value rendered as JSON. There is no Vimshottari Dasha, no Antardasha, no
Navamsha (D9), no transit-to-natal aspects, no Lagna-from-Moon checks, no
Panchaka-rahita / dina-shuddhi factors. The Lagna is computed but never used
in scoring.

Flagged by Judge 4; consistent with Judge 1's point that "inner state" has no
representation.

---

## Per-judge summaries

### Judge 1 — Yogic philosophy alignment

> The project has read Sadhguru and then built a conventional muhurta
> calculator with a yogic preface taped to the front. The philosophical
> scaffolding in `PROJECT_ORIGIN.md` and `YOGIC_PERSPECTIVE.md` is genuinely
> faithful — Kala as a living field, geometry as map, awareness as the goal,
> anti-fatalism as the discipline — but none of it survives the trip into
> `cosmic_engine.py`. The engine is a sum of hard-coded auspicious /
> inauspicious deltas culminating in a five-band verdict, which is precisely
> the "blame the planets" posture the origin document forbids.

Specific flaws:

- **Sadhana / meditation is one of six peer activity tags** in
  `ACTIVITY_PROFILES`, not a first-class axis. Inner consciousness is the
  point of the Sadhguru framing; here it ranks alongside "Investment /
  finance" with the same arithmetic.
- **No human inner-state input.** Inputs are date, location, activity, and
  birth data only. Nothing about breath, sleep, agitation, intention, or
  sandhya practice.
- **Anti-fatalism language lives only in the prose layer** (`README.md`,
  `PROJECT_ORIGIN.md`, the static `principle` string). The executable code
  speaks the opposite dialect (`band = "Avoid"`,
  `cautions.append("Ashtama Chandra caution")`).

### Judge 2 — Astronomical and calculation correctness

Verified correct:

- Tithi index logic, paksha handling, Purnima/Amavasya naming
- Nakshatra span (360/27), Pada (span/4), lord assignment
- Yoga and Karana index formulas
- Kimstughna / Shakuni / Chatushpada / Naga fixed-karana mapping
- Rahu Kala weekday→segment mapping (matches canonical 0-indexed)
- Gulika Kala weekday→segment mapping
- Tara Bala benefic set `{0, 2, 4, 6, 8}` against the 9-Tara cycle
- Chandra Bala houses `{1, 3, 6, 7, 10, 11}`
- Ashtama Chandra at count == 8
- Whole-Sign houses for Lagna

Flagged calculation issues:

- **Ayana / Ritu use Gregorian dates while everything else is sidereal.**
  Persistent ~24-day error against canonical Sankranti boundaries.
- **Yamaganda mapping is suspected wrong for Thursday and Friday.** The judge
  cites canonical Yamaganda as Sun=4, Mon=3, Tue=2, Wed=1, Thu=7, Fri=5,
  Sat=6 (1-indexed). The code's 0-indexed dict gives Thu=0 (segment 1) and
  Fri=6 (segment 7).
  - **Caveat:** the literature on Yamaganda has at least two competing
    schemes (one common South-Indian table reads
    Sun=5, Mon=4, Tue=3, Wed=2, Thu=1, Fri=7, Sat=6 — which the code does
    match). This finding should be verified against the lineage the project
    intends to follow rather than fixed blindly.
- **Abhijit Muhurta** centred on the midpoint of sunrise and sunset (mean
  noon), not true solar noon. Off by up to ±16 minutes (equation of time).
- **Cross-ayanamsha contamination.** `swe.set_sid_mode` is global state;
  `panchangam_for_date` and `birth_chart` accept independent ayanamsha
  arguments. If they are called with different ayanamshas, `chandra_bala`
  compares positions computed under different sidereal frames.
- **NOAA sunrise** is good to ~1–4 min in temperate latitudes; can flip
  borderline Tithi / Vara / Nakshatra. Polar fallback is silent.
- **Hora as fixed 60-minute slabs** instead of variable day-hora /
  night-hora.
- **Tests verify shape, not values.** `test_tara_and_chandra_bala_known_support_flags`
  cross-checks the code against itself; it would still pass if the benefic
  sets were inverted.

### Judge 3 — Software engineering and model design

- **Magic-number cascade.** Scoring magnitudes (50, 20, 12, 10, 8, 7, 6, 0.8,
  1.0, 1.2, 1.4, band cutoffs 85/72/58/42) are inline literals with no
  derivation, no calibration, no override. `documentation/RULES.md` is five
  sentences of platitudes that list zero of the actual rules.
- **README claims a "transparent and configurable model."** False on both
  counts — rules live in code only, no config / env / file override path.
- **Activity-specific hora bonuses bypass `ACTIVITY_PROFILES`.** Three nested
  inline `if activity == "..."` branches mean adding a new activity in
  `ACTIVITY_PROFILES` silently disables hora bonuses for it.
- **Reasons / cautions silently truncated to 6.** Covert information loss in a
  field that is supposed to be the explanation layer.
- **Global swisseph state mutation** (`swe.set_sid_mode`) without a context
  manager — ordering hazard under threaded servers and Streamlit reruns.
- **Naive ISO-string round-trips** through `windows_for_day` and `score_slot`.
  No tz-aware vs naive guard.
- **Polar fallback in `noaa_sunrise_sunset` is silent.** No log, no warning,
  no UI flag.
- **Zero input validation in `app.py`.** Custom lat / lng / timezone strings
  flow straight into computation; invalid timezone raises
  `ZoneInfoNotFoundError` from the engine; lat outside ±90 produces a silent
  NaN cascade.
- **Tests cover the happy path only.** Missing: Karana fixed-karana edges,
  weekday→Rahu/Yamaganda/Gulika mapping, ayanamsha switching, polar fallback,
  band boundaries, hora wraparound, reasons truncation, profile fallback.
  E2E test only checks that strings render — no numeric ground truth.
- **Unreproducible build.** `requirements.txt` uses unbounded `>=` lower
  pins, no lockfile. `pyproject.toml` is a pytest stub with no `[project]`
  metadata. `Dockerfile` has no non-root user, no healthcheck, no pinned
  base-image digest, no `.dockerignore`, copies `.git/`. CI installs
  unpinned deps each run.

### Judge 4 — Jyotish tradition fidelity

> The astronomy is honest, the vocabulary is correct, and the author has
> clearly read the words. But the scoring engine is a Western-style astro-app
> with Sanskrit labels — it computes the five limbs and then ignores three of
> them. A muhurta is the *interaction* of tithi, vara, nakshatra, yoga,
> karana — you cannot drop three legs of the Panchangam, keep nakshatra and
> hora, and call the result a muhurta.

Verified correct:

- Tara Bala benefic set
- Ashtama Chandra flag
- Hora-of-sunrise = vara-lord for all 7 weekdays
- Brahma Muhurta 96–48 min before sunrise (one valid tradition)
- Whole-Sign houses for Lagna (appropriate for Parashari Jyotish)
- Investment / finance `boost_nak` = Dhruva + Mridu set (Rohini, U.Phalguni,
  U.Ashadha, U.Bhadrapada, Revati). Defensible.

Flaws specific to traditional fidelity:

- **No Tithi-class scoring** (Nanda / Bhadra / Jaya / Rikta / Purna).
- **Bhadra Karana not gated.** Most universally avoided karana in classical
  muhurta — engine names it and does nothing.
- **Inauspicious yogas not penalised** (Vyatipata, Vaidhriti, Vyaghata,
  Parigha, Shula, Ganda, Atiganda, Vajra).
- **No Vara-activity matching.** Saturday at noon and Thursday at noon score
  identically for a wedding.
- **Coarse activity buckets.** "Travel" omits Pushya. "Health" omits
  Ashwini-Mrigashirsha pairing for chikitsa. "Ceremony" lumps every saumya
  nakshatra together rather than distinguishing vivaha / upanayana /
  griha-pravesha.
- **Festival / Vrata layer absent.** No Ekadashi, Pradosha, Sankranti,
  Amavasya / Purnima flags, no Panchaka, no Bhadra-mukha / puchha split. For
  a product called Panchangam Dashboard this is conspicuous.
- **Sandhya at ±24 min is one defensible reading**; lineages also use one
  ghati or one full muhurta (48 min).

---

## Single most fundamental flaw

If only one item is to be addressed, it is item #3: **the model claims to be a
Panchangam-Muhurta engine but only scores two of the five limbs**. Every
other flaw — fatalistic banding, missing Vara matching, magic-number
calibration, even the tropical/sidereal Ayana inconsistency — is downstream of
the engine treating Tithi, Yoga, and Karana as display fields rather than as
inputs to the judgement.

Once Tithi-class, Vishti, and the malefic-yoga set actually drive scoring, the
"transparent and configurable model" claim becomes meaningful, the
explanation layer (`reasons` / `cautions`) starts to do real work, and the
yogic framing of "respond, do not react" can be re-grounded — because the user
finally sees *why* a window is what it is, in the language of the tradition
the project says it is honoring.

---

## Recommended next steps (ranked)

1. **Make Tithi-class, Karana (Bhadra), and malefic-yoga scoring first-class
   in `score_slot`.** Drive them from data in `ACTIVITY_PROFILES`, not
   inline.
2. **Replace `ritu_and_ayana` with sidereal Sun-longitude-based Sankranti
   logic.** Compute Uttarayana / Dakshinayana from the Sun's sidereal
   longitude crossing 0° Capricorn / 0° Cancer, not Gregorian dates.
3. **Replace `noaa_sunrise_sunset` with `swe.rise_trans`** and surface the
   polar fallback explicitly.
4. **Make Hora variable-length** (day-hora vs night-hora) and let
   `rank_muhurta_windows` cover the night for sadhana scoring.
5. **Lift scoring magnitudes into a single configurable structure**
   (e.g., `SCORING_WEIGHTS` dict or a YAML file) and document each weight in
   `documentation/RULES.md`.
6. **Add a yogic-state input** — sleep, agitation, intention — and use it to
   modulate `daily_alignment_text` so the Kala→awareness chain is actually
   walked.
7. **Replace the `Avoid` band label with neutral, awareness-oriented language**
   ("low support" / "high friction") to match the stated anti-fatalism.
8. **Add input validation** in `app.py` for lat / lng / timezone.
9. **Pin dependencies** (lockfile or upper bounds) and add a `pyproject.toml`
   with proper `[project]` metadata.
10. **Add tests against canonical Jyotish reference values** for Tara Bala,
    Chandra Bala, Karana fixed-positions, and Rahu/Yamaganda/Gulika weekday
    mappings — not just shape checks.
