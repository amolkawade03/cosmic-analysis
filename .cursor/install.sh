#!/usr/bin/env bash
# Idempotent setup for the Cosmic Analysis dev environment.
# Runs from the repository root after the source has been checked out.
set -euo pipefail

# System packages: compiler + Python headers are required to build the
# pyswisseph C extension, and python3-venv is needed to create the virtualenv.
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  build-essential \
  python3-dev \
  python3-venv

# Project virtualenv + Python dependencies.
python3 -m venv .venv
# shellcheck source=/dev/null
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# Playwright browser + OS-level libraries for the browser-based e2e tests.
python -m playwright install-deps chromium
python -m playwright install chromium
