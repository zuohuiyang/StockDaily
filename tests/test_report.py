import tempfile
import unittest
from pathlib import Path

from stock import db as dbm
from stock.calc import build_daily_report_data
from stock.holdings import HoldingPosition
from stock.reporting import render_markdown


def _fixture_positions() -> list[HoldingPosition]:
    return [
        HoldingPosition(asset_class=dbm.ASSET_CLASS_CN, asset_id="518850", quantity=1.0, currency="CNY", avg_cost=1.0),
        HoldingPosition(asset_class=dbm.ASSET_CLASS_US, asset_id="SOXX", quantity=1.0, currency="USD", avg_cost=1.0),
        HoldingPosition(asset_class=dbm.ASSET_CLASS_CRYPTO, asset_id="ETH", quantity=1.0, currency="USD", avg_cost=1.0),
    ]


class TestReport(unittest.TestCase):
    def test_report_render_and_missing_none(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = str(Path(td) / "portfolio.db")
            with dbm.connect(db_path) as conn:
                dbm.ensure_schema(conn)
                for d in ("2026-01-02", "2026-03-02", "2026-03-03"):
                    dbm.upsert_daily_price(
                        conn,
                        asset_class=dbm.ASSET_CLASS_CN,
                        asset_id="518850",
                        price_date=d,
                        close_price=1.0,
                        quote_ccy="CNY",
                        source="tencent",
                    )
                    dbm.upsert_daily_price(
                        conn,
                        asset_class=dbm.ASSET_CLASS_US,
                        asset_id="SOXX",
                        price_date=d,
                        close_price=10.0,
                        quote_ccy="USD",
                        source="yahoo",
                    )
                    dbm.upsert_daily_price(
                        conn,
                        asset_class=dbm.ASSET_CLASS_CRYPTO,
                        asset_id="ETH",
                        price_date=d,
                        close_price=2.0,
                        quote_ccy="USD",
                        source="coingecko",
                    )
                    dbm.upsert_exchange_rate(
                        conn, from_ccy="USD", to_ccy="CNY", rate_date=d, exchange_rate=7.0, source="x"
                    )
                conn.commit()

                data = build_daily_report_data(conn, positions=_fixture_positions(), report_date="2026-03-03")
            md = render_markdown(data)
            self.assertIn("# StockDaily 日报", md)
            self.assertIn("- 报告日期：2026-03-03", md)
            self.assertIn("- 缺少收盘价：无", md)
            self.assertIn("- 缺少汇率：无", md)
            self.assertIn("| 518850 | CN_STOCK | CNY |", md)
            self.assertIn("| SOXX | US_STOCK | USD |", md)
            self.assertIn("| ETH | CRYPTO | USD |", md)

    def test_missing_fx_excludes_from_total(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = str(Path(td) / "portfolio.db")
            with dbm.connect(db_path) as conn:
                dbm.ensure_schema(conn)
                dbm.upsert_daily_price(
                    conn,
                    asset_class=dbm.ASSET_CLASS_CN,
                    asset_id="518850",
                    price_date="2026-03-03",
                    close_price=1.0,
                    quote_ccy="CNY",
                    source="tencent",
                )
                dbm.upsert_daily_price(
                    conn,
                    asset_class=dbm.ASSET_CLASS_US,
                    asset_id="SOXX",
                    price_date="2026-03-03",
                    close_price=10.0,
                    quote_ccy="USD",
                    source="yahoo",
                )
                dbm.upsert_daily_price(
                    conn,
                    asset_class=dbm.ASSET_CLASS_CRYPTO,
                    asset_id="ETH",
                    price_date="2026-03-03",
                    close_price=2.0,
                    quote_ccy="USD",
                    source="coingecko",
                )
                conn.commit()
                data = build_daily_report_data(conn, positions=_fixture_positions(), report_date="2026-03-03")
            self.assertEqual(data.total_value_cny, 1.0)
            self.assertEqual(set(data.missing_fx), {"ETH", "SOXX"})


if __name__ == "__main__":
    unittest.main()
