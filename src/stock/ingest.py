from __future__ import annotations

import argparse
import re
import sys
from datetime import date as date_type
from datetime import datetime

from stock import db as dbm
from stock.sources import fetch_cn_close_prices, fetch_crypto_close_prices_usd, fetch_us_close_prices, fetch_usd_cny_timeseries


def _parse_date(s: str) -> date_type:
    return datetime.strptime(s, "%Y-%m-%d").date()


_CN_CODE_RE = re.compile(r"^\d{6}$")


def infer_asset_class(asset_id: str) -> str:
    up = asset_id.upper()
    if up in ("BTC", "ETH"):
        return dbm.ASSET_CLASS_CRYPTO
    if _CN_CODE_RE.match(asset_id):
        return dbm.ASSET_CLASS_CN
    return dbm.ASSET_CLASS_US


def infer_quote_ccy(asset_class: str) -> str:
    if asset_class == dbm.ASSET_CLASS_CN:
        return "CNY"
    return "USD"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m stock.ingest")
    parser.add_argument("--db", default="portfolio.db")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("public-backfill")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--symbols", nargs="*")

    p = sub.add_parser("public-daily")
    p.add_argument("--lookback-days", type=int, default=7)
    p.add_argument("--symbols", nargs="*")

    return parser


def _default_range_for_lookback(lookback_days: int) -> tuple[str, str]:
    if lookback_days <= 0:
        raise ValueError("--lookback-days 必须为正数")
    end = date_type.fromordinal(date_type.today().toordinal() - 1)
    start = date_type.fromordinal(end.toordinal() - (lookback_days - 1))
    return start.isoformat(), end.isoformat()


def _resolve_symbols(conn: dbm.sqlite3.Connection, explicit: list[str] | None) -> list[str]:
    if explicit:
        return [str(x) for x in explicit]
    return [a.asset_id for a in dbm.get_active_assets(conn)]


def public_backfill(*, db_path: str, start: str, end: str, symbols: list[str] | None) -> None:
    start_d = _parse_date(start)
    end_d = _parse_date(end)
    if end_d < start_d:
        raise ValueError("--end 必须不早于 --start")

    with dbm.connect(db_path) as conn:
        dbm.ensure_schema(conn)
        resolved = _resolve_symbols(conn, symbols)

        usd_assets: list[str] = []
        cn_assets: list[str] = []
        crypto_assets: list[str] = []
        for asset_id in resolved:
            asset_class = infer_asset_class(asset_id)
            if asset_class != dbm.ASSET_CLASS_CN:
                asset_id = asset_id.upper()
            quote_ccy = infer_quote_ccy(asset_class)
            dbm.upsert_asset(conn, asset_id=asset_id, asset_class=asset_class, quote_ccy=quote_ccy, is_active=1)
            if asset_class == dbm.ASSET_CLASS_CN:
                cn_assets.append(asset_id)
            elif asset_class == dbm.ASSET_CLASS_US:
                usd_assets.append(asset_id)
            else:
                crypto_assets.append(asset_id)

        for asset_id in cn_assets:
            for d, close in fetch_cn_close_prices(asset_id=asset_id, start=start, end=end):
                dbm.upsert_daily_price(
                    conn,
                    asset_class=dbm.ASSET_CLASS_CN,
                    asset_id=asset_id,
                    price_date=d,
                    close_price=close,
                    quote_ccy="CNY",
                    source="tencent",
                )

        for asset_id in usd_assets:
            for d, close in fetch_us_close_prices(asset_id=asset_id, start=start, end=end):
                dbm.upsert_daily_price(
                    conn,
                    asset_class=dbm.ASSET_CLASS_US,
                    asset_id=asset_id,
                    price_date=d,
                    close_price=close,
                    quote_ccy="USD",
                    source="yahoo",
                )

        for asset_id in crypto_assets:
            for d, close in fetch_crypto_close_prices_usd(asset_id=asset_id, start=start, end=end):
                dbm.upsert_daily_price(
                    conn,
                    asset_class=dbm.ASSET_CLASS_CRYPTO,
                    asset_id=asset_id,
                    price_date=d,
                    close_price=close,
                    quote_ccy="USD",
                    source="coingecko",
                )

        for d, rate in fetch_usd_cny_timeseries(start=start, end=end):
            dbm.upsert_exchange_rate(
                conn, from_ccy="USD", to_ccy="CNY", rate_date=d, exchange_rate=rate, source="exchangerate_host"
            )
        conn.commit()


def public_daily(*, db_path: str, lookback_days: int, symbols: list[str] | None) -> None:
    start, end = _default_range_for_lookback(lookback_days)
    public_backfill(db_path=db_path, start=start, end=end, symbols=symbols)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "public-backfill":
            public_backfill(db_path=args.db, start=args.start, end=args.end, symbols=args.symbols)
            return 0
        if args.cmd == "public-daily":
            public_daily(db_path=args.db, lookback_days=args.lookback_days, symbols=args.symbols)
            return 0
        print(f"未知命令: {args.cmd}", file=sys.stderr)
        return 2
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
