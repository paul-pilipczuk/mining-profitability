import unittest
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from mineval import (  
    _clamp01,
    efficiency_j_per_th,
    miner_share,
    hashprice_btc_per_th_day,
    btc_day_net,
    elec_cost_usd_day,
    elec_cost_usd_month
)


class TestClamp(unittest.TestCase):
    def test_clamp_basic(self):
        self.assertEqual(_clamp01(-0.5), 0.0)
        self.assertEqual(_clamp01(0.0), 0.0)
        self.assertEqual(_clamp01(0.42), 0.42)
        self.assertEqual(_clamp01(1.0), 1.0)
        self.assertEqual(_clamp01(1.3), 1.0)

class TestEfficiency(unittest.TestCase):
    def test_efficiency_best_and_edge(self):
        # 3060 W @ 104TH/s converted to J/TH
        self.assertAlmostEqual(efficiency_j_per_th(3060, 104), 3060 / 104, places=12)
        # 0 and neg inputs
        self.assertEqual(efficiency_j_per_th(0, 100), 0.0)
        self.assertEqual(efficiency_j_per_th(3000, 0), 0.0)
        self.assertEqual(efficiency_j_per_th(-1, 100), 0.0)
        self.assertEqual(efficiency_j_per_th(100, -1), 0.0)

class TestMinerShare(unittest.TestCase):
    def test_miner_share(self):
        self.assertAlmostEqual(miner_share(100, 600), 100 / (600*1_000_000), places=18)
        # 0 or neg numbers
        self.assertEqual(miner_share(0, 600), 0.0)
        self.assertEqual(miner_share(100, 0), 0.0)
        self.assertEqual(miner_share(-5, 600), 0.0)
        self.assertEqual(miner_share(100, -1), 0.0)

class TestHashprice(unittest.TestCase):
    def test_hashprice_btc_per_th_day(self):
        # Simple numbers: reward=3, blocks=144, network=600 EH/s
        # hashprice = (144*3) / (600e6) = 432 / 600,000,000 = 7.2e-7 BTC/TH/day
        self.assertAlmostEqual(hashprice_btc_per_th_day(600, 144, 3), 432 / 600_000_000, places=18)
        # 0 or neg numbers
        self.assertEqual(hashprice_btc_per_th_day(0, 144, 3), 0.0)
        self.assertEqual(hashprice_btc_per_th_day(600, 0, 3), 0.0)
        self.assertEqual(hashprice_btc_per_th_day(600, 144, 0), 0.0)
        self.assertEqual(hashprice_btc_per_th_day(-1, 144, 3), 0.0)


class TestBtcDayNet(unittest.TestCase):
    def test_btc_day_net_basic(self):
        # miner=100 TH/s, network=600 EH/s, reward=3.125 BTC/block, 144 blocks/day
        # share = 100 / (600e6) = 1.6666666667e-7
        # gross = share * 144 * 3.125 = 7.5e-5
        # net = gross * (1 - 0.02) * 0.98 = 7.5e-5 * 0.9604 = 7.203e-5
        res = btc_day_net(
            miner_ths=100,
            network_ehs=600,
            blocks_per_day=144,
            reward_per_block_btc=3.125,
            pool_fee=0.02,
            uptime=0.98,
        )
        self.assertAlmostEqual(res, 7.5e-5 * 0.9604, places=12)

    def test_btc_day_net_edge_cases(self):
        self.assertEqual(btc_day_net(0, 600, 144, 3.125, 0.02, 0.98), 0.0)
        self.assertEqual(btc_day_net(100, 0, 144, 3.125, 0.02, 0.98), 0.0)
        self.assertEqual(btc_day_net(100, 600, 0, 3.125, 0.02, 0.98), 0.0)
        self.assertEqual(btc_day_net(100, 600, 144, 0, 0.02, 0.98), 0.0)

    def test_btc_day_net_clamped(self):
        # pool_fee > 1 → clamped to 1 → zero net
        self.assertEqual(btc_day_net(100, 600, 144, 3.125, 1.5, 0.98), 0.0)
        # uptime > 1 → clamped to 1 (compare against uptime=1.0)
        a = btc_day_net(100, 600, 144, 3.125, 0.0, 1.1)
        b = btc_day_net(100, 600, 144, 3.125, 0.0, 1.0)
        self.assertAlmostEqual(a, b, places=18)
        # negative fee / uptime → clamped to 0
        a = btc_day_net(100, 600, 144, 3.125, -0.1, 0.98)  # fee->0
        b = btc_day_net(100, 600, 144, 3.125, 0.0, 0.98)
        self.assertAlmostEqual(a, b, places=18)
        a = btc_day_net(100, 600, 144, 3.125, 0.02, -0.5)  # uptime->0
        self.assertEqual(a, 0.0)

class TestElectricityCosts(unittest.TestCase):
    def test_elec_cost_usd_day_happy(self):
        # 3060 W, $0.08/kWh, uptime 0.98
        # kWh/day = 3.06 * 24 * 0.98 = 71.9712; cost = 71.9712 * 0.08 = 5.757696
        self.assertAlmostEqual(elec_cost_usd_day(3060, 0.08, 0.98), 5.757696, places=9)

    def test_elec_cost_usd_day_edges(self):
        # zero/negative inputs → 0
        self.assertEqual(elec_cost_usd_day(0, 0.1, 1.0), 0.0)
        self.assertEqual(elec_cost_usd_day(1000, 0.0, 1.0), 0.0)
        self.assertEqual(elec_cost_usd_day(-10, 0.1, 1.0), 0.0)
        # uptime clamped to 1.0
        self.assertAlmostEqual(elec_cost_usd_day(1000, 0.10, 1.2), 24 * 0.10, places=12)

    def test_elec_cost_usd_month(self):
        # Simple numbers: 1000 W, $0.10/kWh, uptime 1.0
        # daily = 24 * 0.10 = 2.4 → month (default 30.437) = 73.04...
        self.assertAlmostEqual(elec_cost_usd_month(1000, 0.10, 1.0), 2.4 * 30.437, places=9)
        # custom days
        self.assertAlmostEqual(elec_cost_usd_month(1000, 0.10, 1.0, days_in_month=30), 2.4 * 30, places=9)
        # negative days → clamped to 0
        self.assertEqual(elec_cost_usd_month(1000, 0.10, 1.0, days_in_month=-5), 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)