import unittest
import sqlite3
from stock import db as dbm
from stock.calc import build_daily_report_data
from stock.holdings import HoldingPosition
from stock.reporting import render_markdown

class TestReportFallback(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        dbm.ensure_schema(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_report_fallback_display(self):
        # 1. Setup Data: Price on T-2 (2026-03-04), Target T (2026-03-06)
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
        # FX needed for USD asset
        dbm.upsert_exchange_rate(self.conn, from_ccy="USD", to_ccy="CNY", rate_date="2026-03-06", exchange_rate=7.0, source="test")

        positions = [
            HoldingPosition(asset_class=dbm.ASSET_CLASS_US, asset_id="AAPL", quantity=1.0, currency="USD", avg_cost=100.0)
        ]

        # 2. Build Report Data
        data = build_daily_report_data(self.conn, positions=positions, report_date="2026-03-06")

        # 3. Render Markdown
        md = render_markdown(data)

        # 4. Verify
        # Check if fallback section exists
        self.assertIn("**数据回退**", md)
        self.assertIn("AAPL (使用 2026-03-04)", md)
        # Check if price marked with *
        # Price 150.0 -> "150.00 *"
        self.assertIn("150.00 *", md)

if __name__ == "__main__":
    unittest.main()
