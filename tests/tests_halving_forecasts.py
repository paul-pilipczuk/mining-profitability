import unittest
from pathlib import Path
import sys
import datetime
import math

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))


from mineval import (
    SUBSIDY_GENESIS_BTC,
    HALVING_INTERVAL,
    block_subsidy_from_height,
    block_subsidy_at_date,
    _fit_linear_without_numpy,
    forecast_hashrate_log
)

class TestHalvingSubsidy(unittest.Class):
    def test_block_subsidy_from_height_boundaries(self):
        pass
    def test_block_subsidy_at_date_projection(self):
        pass


class TestLogFit(unittest.Class):
    def test_fit_degenerate_returns_mean(self):
        pass

    def test_forecast_empty_raises(self):
        pass

    def forecast_nonpositive_filtered_raises(self):
        pass

    def test_forecast_constant_series(self):
        pass

    def test_forecast_exponential_growth_daily(self):
        pass

    def test_days_ahead_zero_returns_empty(self):
        pass

if __name__ == '__main__':
    unittest.main(verbosity=2)