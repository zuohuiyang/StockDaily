import os
import unittest

from stock.sources import fetch_crypto_close_prices_usd, fetch_usd_cny_timeseries


class TestSourcesNetwork(unittest.TestCase):
    def setUp(self):
        if os.environ.get("RUN_NETWORK_TESTS") != "1":
            self.skipTest("跳过真实网络测试：设置 RUN_NETWORK_TESTS=1 可启用")

    def test_fetch_eth_close_price_usd_real(self):
        out = fetch_crypto_close_prices_usd(asset_id="ETH", start="2024-03-01", end="2024-03-01")
        self.assertTrue(out)
        d, price = out[-1]
        self.assertEqual(d, "2024-03-01")
        self.assertGreater(price, 100.0)

    def test_fetch_usd_cny_timeseries_real(self):
        out = fetch_usd_cny_timeseries(start="2024-03-01", end="2024-03-01")
        self.assertEqual(len(out), 1)
        d, rate = out[0]
        self.assertEqual(d, "2024-03-01")
        self.assertGreater(rate, 6.0)
        self.assertLess(rate, 8.5)


if __name__ == "__main__":
    unittest.main()

