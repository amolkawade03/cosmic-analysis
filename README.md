# Cosmic Analysis

A Sadhguru-faithful sadhana planner with a Panchangam computational layer.

The project has two layers:

1. **Yogic mode** (`run_yogic_analysis.py` + `yogic_engine.py`) — the
   primary surface. Surfaces sadhana windows (Brahma Muhurta + 3 Sandhyas),
   festival/vrata calendar (Mahashivaratri, Guru Pournima, Buddha Pournima,
   Naga Panchami, Sankrantis, Margali masa), equinox/solstice proximity,
   ritu posture, and Sadhguru-stated regimen practices. Bound by an
   explicit source-fidelity contract — every feature traces to a position
   Sadhguru has stated. **Does NOT produce predictive personal forecasting**
   (kids / career / visa / EB1A / finances) — Sadhguru explicitly opposes
   that frame.

2. **Panchangam engine** (`cosmic_engine.py` + `app.py`) — the
   computational layer that the yogic mode is built on. Provides Panchangam
   five limbs, sidereal Sun/Moon calculations, sandhya windows, and a
   positive-additive (anti-fatalist) muhurta ranking.

> Time / Kala → Sun-Moon-Earth geometry → Panchangam limbs →
> body/mind/action/sadhana alignment.

The model treats Panchangam as a geometry map for responsiveness, not a
verdict on whether to act. It is built on principles distilled in
`documentation/SOURCE_KEY_POINTS.md` and the source-fidelity contract in
`documentation/SADHGURU_YOGIC_MODEL.md`.

## What's in / out (Sadhguru-faithful contract)

**Included:**
- Panchangam five limbs (Tithi / Vara / Nakshatra / Yoga / Karana)
- Sandhya (±20 min around sunrise / noon / sunset / midnight) and
  Brahma Muhurta as first-class sadhana windows
- Astronomical solstice-based ayana (Sadhguru's frame in seed talk)
- Sidereal Sankranti-based ritu
- Festival detection: Pournami, Amavasya, Ekadashi, Pradosham,
  Mahashivaratri, Guru Pournima, Buddha Pournima, Naga Panchami,
  12 Sankrantis, Margali masa
- Sadhguru-stated regimen items (castor oil between Chitra Pournami and
  June solstice, cooling foods in Grishma, Margali cold dip)
- Latitude-intensity weighting for Mahashivaratri (peak at |lat|=11°)
- Daily alignment narrative walking Kala → Awareness
- Chandra Bala (Moon's transit relative to natal Moon) as the only
  per-spouse personalization

**Explicitly excluded** (Sadhguru rejects these frames):
- Predictive personal forecasting (career, kids, visa, finances, etc.)
- Vimshottari Dasha, Antardasha, divisional charts
- Tara Bala in muhurta scoring (nakshatra-as-predictor)
- Doshas as fatalistic constraints (Manglik, Sade Sati)
- Mercury / planetary retrograde caution
- "Avoid" verdict on Rahu Kala / Yamaganda / Gulika Kala
- Sign-based Western tropical zodiac framing

See `documentation/SADHGURU_YOGIC_MODEL.md` for source citations.

## Quick start — yogic mode (recommended)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_yogic_analysis.py
```

This produces a day / week / 30-day-lookahead / month / year report with
sadhana windows, festival markers, ritu posture, and the Mahashivaratri
night plan.

## Streamlit dashboard (legacy panchangam view)

```bash
streamlit run app.py
```

Opens at <http://localhost:8501>. The Streamlit app currently surfaces
the panchangam engine only — yogic-mode features (festival calendar,
equinox proximity, regimen, daily narrative) are CLI-only at the moment.

## Run tests

```bash
pytest tests/test_smoke.py tests/test_integration.py tests/test_yogic_engine.py
```

54 tests cover: Panchangam happy paths, festival anchors against
drikpanchang for 2024-2028, anti-fatalism gate (no "Avoid" band, no
negative scores, friction windows annotated not penalised), source-
fidelity gate (Tara Bala excluded from scoring, Janma Nakshatra still
visible), input validation, latitude-intensity hemisphere symmetry,
regimen rules, narrative chain.

## Docker

```bash
docker build -t cosmic-analysis .
docker run -p 8501:8501 cosmic-analysis
```

(Streamlit only; yogic-mode CLI is invoked via `python run_yogic_analysis.py`.)

## Important note

This is a sadhana planner, not a forecast. Traditional muhurta rules
vary by region, lineage, purpose, and teacher; the engine commits
specifically to Sadhguru's stated yogic perspective and intentionally
excludes classical Jyotish predictive features (Dasha, divisional charts,
Tara Bala) per his stated rejection of those frames. Do not use this as
a substitute for qualified medical, legal, financial, or immigration
guidance.

## Project documents

- `documentation/SOURCE_KEY_POINTS.md` — ten distilled positions from
  the seed talk
- `documentation/SADHGURU_YOGIC_MODEL.md` — feature-by-feature source
  citations (the contract)
- `COUNCIL_REVIEW.md` — first-round LLM-judge review
- `documentation/MUHURTA.md`, `RULES.md`, `CALCULATIONS.md`,
  `PANCHANGAM.md`, `ARCHITECTURE.md` — older docs predating the yogic-
  mode rewrite; consult `SADHGURU_YOGIC_MODEL.md` for current state
