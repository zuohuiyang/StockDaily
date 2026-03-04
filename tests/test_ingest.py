import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from stock import db as dbm
from stock.ingest import public_backfill


class TestIngest(unittest.TestCase):
    def test_public_backfill_writes_tables(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = str(Path(td) / "portfolio.db")

            with patch("stock.ingest.fetch_cn_close_prices", return_value=[("2026-03-03", 1.0)]), patch(
                "stock.ingest.fetch_us_close_prices", return_value=[("2026-03-03", 10.0)]
            ), patch("stock.ingest.fetch_crypto_close_prices_usd", return_value=[("2026-03-03", 2.0)]), patch(
                "stock.ingest.fetch_usd_cny_timeseries", return_value=[("2026-03-03", 7.0)]
            ):
                public_backfill(db_path=db_path, start="2026-03-03", end="2026-03-03", symbols=["518850", "SOXX", "ETH"])

            with dbm.connect(db_path) as conn:
                dbm.ensure_schema(conn)
                c_assets = conn.execute(f"SELECT COUNT(*) AS c FROM {dbm.TABLE_ASSETS}").fetchone()["c"]
                c_cn = conn.execute(f"SELECT COUNT(*) AS c FROM {dbm.TABLE_CN_PRICES}").fetchone()["c"]
                c_us = conn.execute(f"SELECT COUNT(*) AS c FROM {dbm.TABLE_US_PRICES}").fetchone()["c"]
                c_crypto = conn.execute(f"SELECT COUNT(*) AS c FROM {dbm.TABLE_CRYPTO_PRICES}").fetchone()["c"]
                c_fx = conn.execute(f"SELECT COUNT(*) AS c FROM {dbm.TABLE_EXCHANGE_RATES}").fetchone()["c"]
                self.assertEqual(int(c_assets), 3)
                self.assertEqual(int(c_cn), 1)
                self.assertEqual(int(c_us), 1)
                self.assertEqual(int(c_crypto), 1)
                self.assertEqual(int(c_fx), 1)


if __name__ == "__main__":
    unittest.main()
