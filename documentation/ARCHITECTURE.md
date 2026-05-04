# Architecture

Cosmic Analysis has four layers.

## User Interface

The Streamlit app is the entry point. It collects date, location, activity, ayanamsha, and optional personal inputs.

## Calculation Engine

The engine calculates sunrise, sunset, Sun longitude, Moon longitude, Tithi, Vara, Nakshatra, Yoga, Karana, Rashi, Ritu, and Ayana.

## Scoring Engine

The scoring engine divides the day into candidate slots and ranks them for the selected activity.

## Explanation Layer

Each ranked window includes score, band, Hora lord, overlaps, reasons, and cautions.

## Main files

- app.py: Streamlit dashboard
- cosmic_engine.py: calculation and scoring engine
- tests: unit, integration, and browser tests
