from __future__ import annotations

import argparse
import re
import sys
from datetime import date as date_type
from datetime import datetime, timedelta

from stock import db as dbm
from stock.market_hours import check_data_availability
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
    p.add_argument("--force", action="store_true", help="强制覆盖已存在的数据")

    p = sub.add_parser("public-daily")
    p.add_argument("--date", help="目标日报日期 (YYYY-MM-DD)，默认为昨日")
    p.add_argument("--symbols", nargs="*")
    p.add_argument("--force", action="store_true", help="强制覆盖已存在的数据")

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


def _check_price_exists(conn: dbm.sqlite3.Connection, asset_class: str, asset_id: str, price_date: str) -> bool:
    table = dbm.table_for_asset_class(asset_class)
    row = conn.execute(
        f"SELECT 1 FROM {table} WHERE asset_id=? AND price_date=?", (asset_id, price_date)
    ).fetchone()
    return bool(row)


def _check_fx_exists(conn: dbm.sqlite3.Connection, rate_date: str) -> bool:
    row = conn.execute(
        f"SELECT 1 FROM {dbm.TABLE_EXCHANGE_RATES} WHERE from_ccy='USD' AND to_ccy='CNY' AND rate_date=?",
        (rate_date,),
    ).fetchone()
    return bool(row)


def ingest_range(
    conn: dbm.sqlite3.Connection,
    *,
    start: str,
    end: str,
    symbols: list[str],
    force: bool = False,
) -> None:
    """
    通用范围拉取逻辑，支持 check-then-fetch
    """
    resolved = _resolve_symbols(conn, symbols)

    usd_assets: list[str] = []
    cn_assets: list[str] = []
    crypto_assets: list[str] = []

    # 1. Ensure assets exist in DB
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

    # Helper to process fetch
    def process_fetch(asset_id: str, asset_class: str, fetch_func, source: str):
        # 如果不是强制刷新，先检查该范围内是否缺数据
        # 简化策略：如果 check-then-fetch，我们应该按日检查。
        # 但 API 是按 range 拉取的。
        # 折中方案：检查 start 和 end 两端，或者如果 range 很短（<=5天），逐日检查。
        # 这里的场景通常是 daily (1-5天) 或 backfill (长)。
        # 如果是 daily，逐日检查很有价值。
        
        start_d = _parse_date(start)
        end_d = _parse_date(end)
        days = (end_d - start_d).days + 1
        
        missing_dates = []
        if not force and days <= 10: # 仅对短范围做精细检查
            for i in range(days):
                d = (start_d + timedelta(days=i)).isoformat()
                if not _check_price_exists(conn, asset_class, asset_id, d):
                    missing_dates.append(d)
            if not missing_dates:
                return # 全部存在，跳过
        
        # 如果需要拉取，直接拉取整个范围（或缺失的最早到最晚）
        # 为了利用 API 的批量能力，通常拉取范围比多次单日拉取快
        
        # 执行可用性检查 (针对 end date)
        # 注意：这里我们只检查 end date 的可用性作为 warning，但不阻止拉取（因为可能拉取旧数据）
        # 实际的 check_data_availability 更多用于 daily 场景
        
        for d, close in fetch_func(asset_id=asset_id, start=start, end=end):
            # 再次检查：如果非 force 且已存在，可以跳过 upsert (虽然 upsert 开销不大，但减少 DB I/O)
            # 这里直接 upsert 即可，因为 fetch 已经发生了
            dbm.upsert_daily_price(
                conn,
                asset_class=asset_class,
                asset_id=asset_id,
                price_date=d,
                close_price=close,
                quote_ccy="USD" if asset_class != dbm.ASSET_CLASS_CN else "CNY",
                source=source,
            )

    for asset_id in cn_assets:
        process_fetch(asset_id, dbm.ASSET_CLASS_CN, fetch_cn_close_prices, "tencent")

    for asset_id in usd_assets:
        process_fetch(asset_id, dbm.ASSET_CLASS_US, fetch_us_close_prices, "yahoo")

    for asset_id in crypto_assets:
        process_fetch(asset_id, dbm.ASSET_CLASS_CRYPTO, fetch_crypto_close_prices_usd, "coingecko")

    # FX
    # FX 也做类似检查
    start_d = _parse_date(start)
    end_d = _parse_date(end)
    days = (end_d - start_d).days + 1
    need_fx = False
    if not force and days <= 10:
        for i in range(days):
            d = (start_d + timedelta(days=i)).isoformat()
            if not _check_fx_exists(conn, d):
                need_fx = True
                break
    else:
        need_fx = True

    if need_fx:
        for d, rate in fetch_usd_cny_timeseries(start=start, end=end):
            dbm.upsert_exchange_rate(
                conn, from_ccy="USD", to_ccy="CNY", rate_date=d, exchange_rate=rate, source="exchangerate_host"
            )
    
    conn.commit()


def public_backfill(*, db_path: str, start: str, end: str, symbols: list[str] | None, force: bool = False) -> None:
    start_d = _parse_date(start)
    end_d = _parse_date(end)
    if end_d < start_d:
        raise ValueError("--end 必须不早于 --start")

    with dbm.connect(db_path) as conn:
        dbm.ensure_schema(conn)
        ingest_range(conn, start=start, end=end, symbols=symbols, force=force)


def public_daily(*, db_path: str, date: str | None, symbols: list[str] | None, force: bool = False) -> None:
    """
    智能日报数据采集：
    1. 确定 Target Date (默认为昨日)
    2. 自动处理依赖日期：Target, Previous (T-1), Year Start
    3. 自动回退范围：如果 Target 是非交易日，向前检查 5 天
    """
    if date:
        target_date = _parse_date(date)
    else:
        # 默认昨日
        target_date = date_type.fromordinal(date_type.today().toordinal() - 1)
    
    # 1. Year Start (YYYY-01-01 to YYYY-01-05 to be safe)
    year_start = date_type(target_date.year, 1, 1)
    year_start_end = date_type(target_date.year, 1, 5) # 拉取年初前5天，确保有数据
    
    # 2. Target Range (Target - 5 days to Target)
    # 向前多拉几天，以备回退和计算环比 (Previous Day)
    target_start = target_date - timedelta(days=5)
    
    with dbm.connect(db_path) as conn:
        dbm.ensure_schema(conn)
        
        # Ingest Year Start
        print(f"Checking Year Start data [{year_start} - {year_start_end}]...")
        ingest_range(conn, start=year_start.isoformat(), end=year_start_end.isoformat(), symbols=symbols, force=force)
        
        # Ingest Target Range
        print(f"Checking Recent data [{target_start} - {target_date}]...")
        ingest_range(conn, start=target_start.isoformat(), end=target_date.isoformat(), symbols=symbols, force=force)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "public-backfill":
            public_backfill(db_path=args.db, start=args.start, end=args.end, symbols=args.symbols, force=args.force)
            return 0
        if args.cmd == "public-daily":
            public_daily(db_path=args.db, date=args.date, symbols=args.symbols, force=args.force)
            return 0
        print(f"未知命令: {args.cmd}", file=sys.stderr)
        return 2
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
