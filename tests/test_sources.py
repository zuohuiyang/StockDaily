import unittest
from unittest.mock import patch

from stock.sources import fetch_crypto_close_prices_usd


class TestSources(unittest.TestCase):
    def test_fetch_crypto_close_prices_usd_cryptocompare_parsing(self):
        fake = {
            "Data": {
                "Data": [
                    {"time": 1709164800, "close": 3342.24},
                    {"time": 1709251200, "close": 3435.90},
                ]
            }
        }
        with patch("stock.sources.get_json", return_value=fake) as m:
            out = fetch_crypto_close_prices_usd(asset_id="ETH", start="2024-03-01", end="2024-03-01")
            self.assertEqual(out, [("2024-03-01", 3435.9)])
            self.assertTrue(m.called)

    def test_fetch_crypto_close_prices_usd_rejects_unknown_symbol(self):
        with patch("stock.sources.get_json") as m:
            out = fetch_crypto_close_prices_usd(asset_id="DOGE", start="2024-03-01", end="2024-03-01")
            self.assertEqual(out, [])
            m.assert_not_called()


if __name__ == "__main__":
    unittest.main()

