import os
import csv
from pathlib import Path
import datetime

# Constants for Bitcoin mining evaluation

BLOCKS_PER_DAY_DEFAULT = 144.0
SUBSIDY_GENESIS_BTC = 50.0
HALVING_INTERVAL = 210000

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_MINERS = PROJECT_ROOT / "data" / "miners.csv"
DEFAULT_HISTORY = PROJECT_ROOT / "data" / "hashrate.csv"
DEFAULT_OUT = PROJECT_ROOT / "output" / "results.csv"
DEFAULT_TIMELINE = PROJECT_ROOT / "output" / "timeline.csv"
DEFAULT_CHART_DIR = PROJECT_ROOT / "output" / "charts"


def read_miners(path):
    """Read miners from a CSV file and return a list of dictionaries, headers required."""
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"miners.csv not found at {p}")
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
    

def read_history(path):
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    
    out = []
    with p.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d = datetime.date.fromisoformat(row["date"])
            h = float(row["network_hashrate_ehs"])
            out.append((d, h))
    out.sort(key=lambda x: x[0])
    return out