import tempfile
import unittest
from pathlib import Path

from stock import db as dbm


class TestDb(unittest.TestCase):
    def test_schema_and_upsert_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = str(Path(td) / "portfolio.db")
            with dbm.connect(db_path) as conn:
                dbm.ensure_schema(conn)
                dbm.upsert_asset(conn, asset_id="518850", asset_class=dbm.ASSET_CLASS_CN, quote_ccy="CNY", is_active=1)
                dbm.upsert_asset(conn, asset_id="518850", asset_class=dbm.ASSET_CLASS_CN, quote_ccy="CNY", is_active=1)

                dbm.upsert_daily_price(
                    conn,
                    asset_class=dbm.ASSET_CLASS_CN,
                    asset_id="518850",
                    price_date="2026-03-03",
                    close_price=1.23,
                    quote_ccy="CNY",
                    source="tencent",
                )
                dbm.upsert_daily_price(
                    conn,
                    asset_class=dbm.ASSET_CLASS_CN,
                    asset_id="518850",
                    price_date="2026-03-03",
                    close_price=1.23,
                    quote_ccy="CNY",
                    source="tencent",
                )

                dbm.upsert_exchange_rate(
                    conn, from_ccy="USD", to_ccy="CNY", rate_date="2026-03-03", exchange_rate=7.2, source="x"
                )
                dbm.upsert_exchange_rate(
                    conn, from_ccy="USD", to_ccy="CNY", rate_date="2026-03-03", exchange_rate=7.2, source="x"
                )
                conn.commit()

                assets = dbm.get_active_assets(conn)
                self.assertEqual(len(assets), 1)

                rows = conn.execute(f"SELECT COUNT(*) AS c FROM {dbm.TABLE_CN_PRICES}").fetchone()
                self.assertEqual(int(rows["c"]), 1)

                rows = conn.execute(f"SELECT COUNT(*) AS c FROM {dbm.TABLE_EXCHANGE_RATES}").fetchone()
                self.assertEqual(int(rows["c"]), 1)


if __name__ == "__main__":
    unittest.main()

