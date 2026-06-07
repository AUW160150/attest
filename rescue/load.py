"""Load the Harven warehouse records + customer master."""
from __future__ import annotations

import csv

from . import config


def load_records() -> list[dict]:
    with open(config.RECORDS_CSV, newline="") as f:
        return list(csv.DictReader(f))


def load_customers() -> dict[str, dict]:
    with open(config.CUSTOMERS_CSV, newline="") as f:
        return {r["customer_id"]: r for r in csv.DictReader(f)}
