import os
import csv
from pathlib import Path


def read_miners(path):
    """Read miners from a CSV file and return a list of dictionaries, headers required."""
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"miners.csv not found at {p}")
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))