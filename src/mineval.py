import os
import csv
from pathlib import Path
import datetime
from typing import Tuple, Dict, List, Optional
import math

# This is for future implementation to auto-run query for hashrate.csv
# try:
#     import requests
# except Exception:
#     requests = None



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

# ---------- CORE MINING AND COST MATH ----------

def _clamp01(x: float) -> float:
    """Clamp to [0, 1] useful for fractions like pool fee, uptime. Makes them safer."""
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def efficiency_j_per_th(power_watts: float, hashrate_ths: float) -> float:
    """
    Return energy efficiency in J/TH. 0 if inputs are not positive.
    Some Physics here to explain the units:
    J/TH = (Watts / TH/s). (Watts are Joules per second.)
    """
    if power_watts <= 0.0 or hashrate_ths <= 0.0:
        return 0.0
    return power_watts / hashrate_ths


def miner_share(miner_ths: float, network_ehs: float) -> float:
    """
    Fraction of network hashrate controlled by the miner.
    Inputs:
      - miner_ths: miner hashrate in TH/s
      - network_ehs: network hashrate in EH/s
    Returns 0 if inputs are non-positive.
    """
    if miner_ths <= 0.0 or network_ehs <= 0.0:
        return 0.0
    network_ths = network_ehs * 1_000_000.0
    return miner_ths / network_ths


def hashprice_btc_per_th_day(
    network_ehs: float,
    blocks_per_day: float,
    reward_per_block_btc: float,
) -> float:
    """
    Gross revenue in BTC per TH per day, before pool fee & uptime.
    hashprice_btc = (blocks_per_day * reward_per_block_btc) / (network_ths)
    """
    if network_ehs <= 0.0 or blocks_per_day <= 0.0 or reward_per_block_btc <= 0.0:
        return 0.0
    network_ths = network_ehs * 1_000_000.0
    return (blocks_per_day * reward_per_block_btc) / network_ths


def btc_day_net(
    miner_ths: float,
    network_ehs: float,
    blocks_per_day: float,
    reward_per_block_btc: float,
    pool_fee: float,
    uptime: float,
) -> float:
    """
    Expected BTC/day for a single miner, net of pool fee and uptime.

    Notes:
      - miner_ths is TH/s; network_ehs is EH/s
      - pool_fee and uptime are fractions (e.g., 0.02, 0.98); they are clamped to [0,1]
    """
    if miner_ths <= 0.0 or network_ehs <= 0.0 or blocks_per_day <= 0.0 or reward_per_block_btc <= 0.0:
        return 0.0

    pool_fee = _clamp01(pool_fee)
    uptime = _clamp01(uptime)

    share = miner_share(miner_ths, network_ehs)
    gross_btc_day = share * blocks_per_day * reward_per_block_btc
    return gross_btc_day * (1.0 - pool_fee) * uptime


def elec_cost_usd_day(power_watts: float, power_cost_usd_kwh: float, uptime: float) -> float:
    """
    Daily electricity cost in USD for a miner.

      kWh/day = (W / 1000) * 24 * uptime
      cost    = kWh/day * $/kWh
    """
    if power_watts <= 0.0 or power_cost_usd_kwh <= 0.0:
        return 0.0
    uptime = _clamp01(uptime)
    kwh_day = (power_watts / 1000.0) * 24.0 * uptime
    return kwh_day * power_cost_usd_kwh


def elec_cost_usd_month(power_watts: float, power_cost_usd_kwh: float, uptime: float, days_in_month: float = 30.437) -> float:
    """
    Monthly electricity cost in USD. Uses 30.437 days (average month) by default.
    """
    return elec_cost_usd_day(power_watts, power_cost_usd_kwh, uptime) * max(0.0, days_in_month)


# ---------- HALVING_AWARE SUBSIDY CALCS ----------

def block_subsidy_from_height(height: int) -> float:
    """
    Return the block subsidy in BTC for a given block height.
    Safeguards:
      - height < 0 -> 0
      - after 33 it is effectively 0
    """
    h = max(0, int(height))
    halving = h // HALVING_INTERVAL
    if halving >= 33:
        return 0.0
    return SUBSIDY_GENESIS_BTC / (2 ** halving)

def block_subsidy_at_date(d: datetime.date, ref_date: datetime.date, ref_height: int, blocks_per_day:float) -> float:
    """
    Estimate the block subsidy at calendar date 'd' by projecting height from
    a reference (ref_date, ref_height) using constant blocks_per_day.
    """
    delta_days = (d - ref_date).days
    est_height = ref_height + int(round(delta_days * blocks_per_day))
    if est_height < 0:
        # prevents us from getting a negative height 
        est_height = 0
    return block_subsidy_from_height(est_height)

# ---------- HASHRATE FORECASTING (NO DEPS) ----------

def _fit_linear_without_numpy(xs: List[float], ys_log: List[float]) -> Tuple[float, float]:
    #TODO: Fit y = a*x +b in least squares, no numpy
    return False

def forecast_hashrate_log(history: List[Tuple[datetime.date, float]], days_ahead: int) -> List[float]:
    #TODO: Forecast network EH/s for t=1..days_ahead using a log-linear model
    return False