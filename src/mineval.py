import os
import csv
from pathlib import Path
import datetime

try:
    import requests
except Exception:
    requests = None

# Constants & defaults for Bitcoin mining evaluation

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


from typing import Dict, List, Optional

def _normalize_row(row: Dict[str, str]) -> Dict[str, Optional[str]]:
    """Lowercase + strip keys; strip string values. Keeps None as None."""
    out: Dict[str, Optional[str]] = {}
    for k, v in row.items():
        nk = (k or "").strip().lower()
        if isinstance(v, str):
            out[nk] = v.strip()
        else:
            out[nk] = v
    return out


def read_miners(path: str) -> List[Dict[str, str]]:
    """Read miners CSV -> list of dicts with normalized (lowercased) headers."""
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"miners.csv not found at {p}")
    rows: List[Dict[str, str]] = []
    with p.open(newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for raw in rdr:
            rows.append(_normalize_row(raw))  # type: ignore
    return rows


def read_history_ext(path: Optional[str]) -> List[Dict[str, object]]:
    """
    Read weekly hashrate history CSV with tolerant headers.

    Expected columns (normalized / aliases accepted):
      - date | week_start
      - network_hashrate_ehs | hashrate_ehs | network_hash_rate_ehs | ehs
      - block_subsidy_btc | block_reward_btc          (optional)
      - btc_usd | price_usd | btc_price_usd           (optional)
    """
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []

    out: List[Dict[str, object]] = []
    with p.open(newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for raw in rdr:
            row = _normalize_row(raw)

            # --- date (support 'week_start') ---
            d_s = row.get("date") or row.get("week_start")
            if not d_s:
                continue  # skip malformed row
            d = datetime.date.fromisoformat(d_s)

            # --- ehs (support multiple spellings) ---
            ehs_str = (
                row.get("network_hashrate_ehs")
                or row.get("hashrate_ehs")
                or row.get("network_hash_rate_ehs")
                or row.get("ehs")
            )
            if not ehs_str:
                # no hashrate column -> skip row
                continue
            ehs = float(ehs_str)

            # --- subsidy (optional; support alias) ---
            sub_s = row.get("block_subsidy_btc") or row.get("block_reward_btc")
            subsidy = float(sub_s) if sub_s not in (None, "",) else None

            # --- price (optional; support aliases) ---
            price_s = row.get("btc_usd") or row.get("price_usd") or row.get("btc_price_usd")
            btc_usd = float(price_s) if price_s not in (None, "",) else None

            out.append({"date": d, "ehs": ehs, "subsidy": subsidy, "btc_usd": btc_usd})

    out.sort(key=lambda x: x["date"])  # ascending by date
    return out


# ---------- SIMPLE HELPERS ----------

def latest_network_ehs(history: List[Dict[str, object]]) -> Optional[float]:
    return float(history[-1]["ehs"]) if history else None


def latest_btc_price(history: List[Dict[str, object]]) -> Optional[float]:
    for row in reversed(history):
        if row.get("btc_usd") is not None:
            return float(row["btc_usd"])  # ignore
    return None


def parse_float(row: Dict[str, str], key: str, default: float = 0.0) -> float:
    """
    Robust float parser: trims, handles None/empty/missing->default.
    """
    val = row.get(key, "")
    s = "" if val is None else str(val).strip()
    if s == "":
        return default
    try:
        return float(s)
    except Exception:
        return default


def discount_daily_rate(apy: float) -> float:
    return (1.0 + apy) ** (1.0 / 365.0) - 1.0