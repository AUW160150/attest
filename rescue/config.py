"""Shared config for the Data Rescue pipeline (Harven Manufacturing, Track 01)."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import os

BASE_DIR = Path(__file__).resolve().parent.parent  # hack/
DATA = BASE_DIR / "data"
OUTPUT = BASE_DIR / "output"
MEMORY_DIR = OUTPUT / "memory"
OUTPUT.mkdir(exist_ok=True)
MEMORY_DIR.mkdir(exist_ok=True)


def load_env() -> None:
    p = BASE_DIR / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ[k.strip()] = v.strip().strip('"').strip("'")


def get_env(key: str, required: bool = False):
    load_env()
    v = os.environ.get(key)
    if required and not v:
        raise RuntimeError(f"Missing {key} (set it in hack/.env)")
    return v

RECORDS_CSV = DATA / "track01_data_rescue.csv"
CUSTOMERS_CSV = DATA / "track01_customers.csv"

# Audit reference date — anything produced/shipped after this is impossible ("the future").
AUDIT_DATE = dt.date(2026, 6, 7)
