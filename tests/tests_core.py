import unittest
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from mineval import (  
    read_miners,
    read_history_ext,   
    latest_network_ehs,
    latest_btc_price,
    parse_float,
    discount_daily_rate
)


class TestClamp(unittest.TestCase):
    pass

class TestEfficiency(unittest.TestCase):
    pass

class TestMinerShare(unittest.TestCase):
    pass

class TestHashprice(unittest.TestCase):
    pass

class TestBtcDayNet(unittest.TestCase):
    pass

class TestElectricityCosts(unittest.TestCase):
    pass

if __name__ == "__main__":
    unittest.main(verbosity=2)