import json
import tempfile
import unittest
from pathlib import Path

from stock.holdings import load_holdings_json, parse_position_arg


class TestHoldings(unittest.TestCase):
    def test_load_holdings_json(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "holdings.json"
            p.write_text(
                json.dumps(
                    {
                        "as_of": "2026-03-04",
                        "positions": [
                            {
                                "asset_class": "CN_STOCK",
                                "asset_id": "518850",
                                "quantity": 1,
                                "currency": "CNY",
                                "avg_cost": 1.0,
                            },
                            {
                                "asset_class": "US_STOCK",
                                "asset_id": "SOXX",
                                "quantity": 1,
                                "currency": "USD",
                                "avg_cost": 1.0,
                            },
                            {
                                "asset_class": "CRYPTO",
                                "asset_id": "ETH",
                                "quantity": 1,
                                "currency": "USD",
                                "avg_cost": 1.0,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            positions = load_holdings_json(str(p))
            self.assertEqual([x.asset_id for x in positions], ["518850", "SOXX", "ETH"])
            self.assertEqual([x.quantity for x in positions], [1.0, 1.0, 1.0])

    def test_parse_position_arg(self):
        p = parse_position_arg("SOXX:1")
        self.assertEqual(p.asset_id, "SOXX")
        self.assertEqual(p.quantity, 1.0)

        p = parse_position_arg("eth:1")
        self.assertEqual(p.asset_id, "ETH")
        self.assertEqual(p.asset_class, "CRYPTO")
        self.assertEqual(p.currency, "USD")
        self.assertEqual(p.quantity, 1.0)


if __name__ == "__main__":
    unittest.main()
