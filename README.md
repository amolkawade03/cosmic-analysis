# Cosmic Analysis

A Streamlit dashboard for **Panchangam**, **Muhurta window ranking**, and **personal birth-chart integration**.

The project follows a simple first-principles model:

> Time / Kala → Sun-Moon-Earth geometry → Panchangam limbs → body/mind/action/sadhana alignment.

It is built to support reflective planning, not fatalism. The model treats Panchangam as a geometry map for responsiveness.

## Features

- Panchangam five limbs at local sunrise:
  - Tithi
  - Vara
  - Nakshatra
  - Yoga
  - Karana
- Sunrise, sunset, Brahma Muhurta, Sandhya, Abhijit Muhurta, Rahu Kala, Yamaganda, Gulika Kala
- Sidereal Sun/Moon calculations with selectable ayanamsha
- Birth chart personalization:
  - Janma Nakshatra
  - Janma Rashi
  - Lagna / Ascendant
  - Planetary sidereal placements
- Muhurta ranking by activity:
  - Sadhana / meditation
  - Deep work / study
  - Investment / finance
  - Travel
  - Ceremony / auspicious start
  - Health / body reset
- Personal compatibility factors:
  - Tara Bala
  - Chandra Bala
  - Ashtama Chandra caution
- Streamlit dashboard and Python engine
- CI smoke tests

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

## Run tests

```bash
pytest -q
```

## Docker

```bash
docker build -t cosmic-analysis .
docker run -p 8501:8501 cosmic-analysis
```

## Important note

This is a transparent and configurable model. Traditional muhurta rules vary by region, lineage, purpose, and teacher. Do not use this as a substitute for qualified guidance for marriage, childbirth, surgery, legal, medical, or major financial decisions.
