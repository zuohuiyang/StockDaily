import unittest
from unittest.mock import patch, MagicMock
from datetime import date, timedelta
import sqlite3
from stock import db as dbm
from stock.ingest import ingest_range, public_daily

class TestSmartIngest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        dbm.ensure_schema(self.conn)

    def tearDown(self):
        self.conn.close()

    @patch("stock.ingest.fetch_cn_close_prices")
    def test_check_then_fetch_skips_existing(self, mock_fetch):
        # 1. Insert initial data
        dbm.upsert_asset(self.conn, asset_id="600519", asset_class=dbm.ASSET_CLASS_CN, quote_ccy="CNY", is_active=1)
        dbm.upsert_daily_price(
            self.conn,
            asset_class=dbm.ASSET_CLASS_CN,
            asset_id="600519",
            price_date="2026-03-05",
            close_price=100.0,
            quote_ccy="CNY",
            source="test"
        )
        self.conn.commit()

        # 2. Call ingest_range for the same date (without force)
        ingest_range(self.conn, start="2026-03-05", end="2026-03-05", symbols=["600519"], force=False)

        # 3. Assert fetch was NOT called
        mock_fetch.assert_not_called()

    @patch("stock.ingest.fetch_cn_close_prices")
    def test_check_then_fetch_fetches_missing(self, mock_fetch):
        # 1. Mock fetch return
        mock_fetch.return_value = [("2026-03-06", 101.0)]

        # 2. Call ingest_range for a missing date
        ingest_range(self.conn, start="2026-03-06", end="2026-03-06", symbols=["600519"], force=False)

        # 3. Assert fetch WAS called
        mock_fetch.assert_called_once()
        
        # 4. Verify data inserted
        row = self.conn.execute("SELECT close_price FROM cn_stock_prices_daily WHERE asset_id='600519' AND price_date='2026-03-06'").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["close_price"], 101.0)

    def test_get_latest_prices_fallback(self):
        # 1. Insert data for T-2 (2026-03-04)
        dbm.upsert_asset(self.conn, asset_id="AAPL", asset_class=dbm.ASSET_CLASS_US, quote_ccy="USD", is_active=1)
        dbm.upsert_daily_price(
            self.conn,
            asset_class=dbm.ASSET_CLASS_US,
            asset_id="AAPL",
            price_date="2026-03-04",
            close_price=150.0,
            quote_ccy="USD",
            source="test"
        )
        
        # 2. Request price for T (2026-03-06)
        # Should fallback to T-2
        prices = dbm.get_latest_prices(self.conn, asset_class=dbm.ASSET_CLASS_US, asset_ids=["AAPL"], max_date="2026-03-06", lookback_days=5)
        
        self.assertIn("AAPL", prices)
        effective_date, price = prices["AAPL"]
        self.assertEqual(effective_date, "2026-03-04")
        self.assertEqual(price, 150.0)

if __name__ == "__main__":
    unittest.main()
