import unittest
from pathlib import Path
import sys
import datetime

# Make `src/` importable so we can import mineval.py directly
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from mineval import (  # noqa: E402
    read_miners,
    read_history_ext,    # use the canonical function
    latest_network_ehs,
    latest_btc_price,
    parse_float,
    discount_daily_rate,
    # keep read_history shim if you want: read_history,
)

TEST_DIR = Path(__file__).parent
DATA_DIR = TEST_DIR / "data"


class TestReadMiners(unittest.TestCase):
    def test_read_miners_valid(self):
        rows = read_miners(str(DATA_DIR / "miners_valid.csv"))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["name"], "Antminer S19j Pro 104T")
        # brand column is present in the fixture; verify a couple fields
        self.assertEqual(rows[0]["brand"], "antminer")
        self.assertEqual(rows[0]["hashrate_ths"], "104")
        self.assertEqual(rows[0]["power_watts"], "3060")

    def test_read_miners_missing_file_raises(self):
        with self.assertRaises(SystemExit) as cm:
            read_miners(str(DATA_DIR / "nonexistent.csv"))
        self.assertIn("miners.csv not found", str(cm.exception))


class TestReadHistoryExt(unittest.TestCase):
    def test_none_path_returns_empty(self):
        self.assertEqual(read_history_ext(None), [])

    def test_missing_path_returns_empty(self):
        self.assertEqual(read_history_ext(str(DATA_DIR / "does_not_exist.csv")), [])

    def test_parses_full_fields_and_sorts(self):
        rows = read_history_ext(str(DATA_DIR / "hashrate_full.csv"))
        # Sorted ascending by date (file is intentionally unsorted)
        dates = [r["date"] for r in rows]
        self.assertEqual(dates, sorted(dates))

        # Types present
        self.assertIsInstance(rows[0]["ehs"], float)
        self.assertIsInstance(rows[0]["subsidy"], float)
        self.assertIsInstance(rows[0]["btc_usd"], float)

        # First row after sort (2015-01-05)
        self.assertEqual(rows[0]["date"], datetime.date(2015, 1, 5))
        self.assertAlmostEqual(rows[0]["ehs"], 0.35, places=6)
        self.assertAlmostEqual(rows[0]["subsidy"], 25.0, places=6)
        self.assertAlmostEqual(rows[0]["btc_usd"], 280.0, places=2)

        # Last row after sort (2025-01-07)
        self.assertEqual(rows[-1]["date"], datetime.date(2025, 1, 7))
        self.assertAlmostEqual(rows[-1]["ehs"], 600.0, places=6)
        self.assertAlmostEqual(rows[-1]["subsidy"], 3.125, places=6)
        self.assertAlmostEqual(rows[-1]["btc_usd"], 42000.0, places=2)

    def test_alias_block_reward_and_missing_price(self):
        rows = read_history_ext(str(DATA_DIR / "hashrate_alias.csv"))
        self.assertEqual(len(rows), 2)
        # Subsidy should come from block_reward_btc alias
        self.assertAlmostEqual(rows[0]["subsidy"], 6.25, places=6)
        # Second row missing price -> None
        self.assertIsNone(rows[1]["btc_usd"])

    def test_minimal_schema_optional_missing(self):
        rows = read_history_ext(str(DATA_DIR / "hashrate_minimal.csv"))
        self.assertEqual(len(rows), 2)
        # Optional fields are None
        self.assertIsNone(rows[0]["subsidy"])
        self.assertIsNone(rows[0]["btc_usd"])
        self.assertIsInstance(rows[0]["ehs"], float)


class TestLatestHelpers(unittest.TestCase):
    def test_latest_network_ehs_empty(self):
        self.assertIsNone(latest_network_ehs([]))

    def test_latest_network_ehs_nonempty(self):
        hist = read_history_ext(str(DATA_DIR / "hashrate_full.csv"))
        self.assertAlmostEqual(latest_network_ehs(hist), 600.0, places=6)

    def test_latest_btc_price_empty(self):
        self.assertIsNone(latest_btc_price([]))

    def test_latest_btc_price_most_recent_non_none(self):
        hist = [
            {"date": datetime.date(2020, 1, 1), "ehs": 100.0, "btc_usd": None},
            {"date": datetime.date(2020, 1, 8), "ehs": 110.0, "btc_usd": 10000.0},
            {"date": datetime.date(2020, 1, 15), "ehs": 120.0, "btc_usd": None},
            {"date": datetime.date(2020, 1, 22), "ehs": 130.0, "btc_usd": 12000.0},
        ]
        self.assertEqual(latest_btc_price(hist), 12000.0)


class TestParseAndDiscount(unittest.TestCase):
    def test_parse_float_variants(self):
        row = {"ok": "3.14", "space": "  2.5  ", "empty": "", "bad": "abc", "none": None}
        self.assertAlmostEqual(parse_float(row, "ok", 0.0), 3.14, places=6)
        self.assertAlmostEqual(parse_float(row, "space", 0.0), 2.5, places=6)
        # fallbacks to default
        self.assertEqual(parse_float(row, "missing", 7.0), 7.0)
        self.assertEqual(parse_float(row, "empty", 9.0), 9.0)
        self.assertEqual(parse_float(row, "bad", -1.0), -1.0)
        self.assertEqual(parse_float(row, "none", 42.0), 42.0)

    def test_discount_daily_rate(self):
        self.assertAlmostEqual(discount_daily_rate(0.0), 0.0)
        r_pos = discount_daily_rate(0.20)
        self.assertTrue(0 < r_pos < 0.001)  # ~0.0005..0.0006
        self.assertAlmostEqual(r_pos, (1.2 ** (1/365)) - 1, places=12)

        r_neg = discount_daily_rate(-0.10)
        self.assertTrue(r_neg < 0)
        self.assertAlmostEqual(r_neg, ((1 - 0.10) ** (1/365)) - 1, places=12)


if __name__ == "__main__":
    unittest.main(verbosity=2)