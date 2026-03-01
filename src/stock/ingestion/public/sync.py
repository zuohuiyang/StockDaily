from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from urllib.error import URLError, HTTPError

from stock.db.connect import connect
from stock.db.schema import ensure_schema
from stock.ingestion.public.a_share_tencent import fetch_close_prices as fetch_cn
from stock.ingestion.public.fx_exchangerate_host import fetch_usd_cny_timeseries
from stock.ingestion.public.symbols import Symbol, infer_market_currency, load_active_symbols
from stock.ingestion.public.us_share_yahoo import fetch_close_prices as fetch_us


@dataclass(frozen=True)
class IngestionStats:
    symbols: int
    prices_rows: int
    fx_rows: int


def _date_range_for_sync(lookback_days: int) -> tuple[str, str]:
    end = date.today().isoformat()
    start = date.fromordinal(date.today().toordinal() - max(lookback_days, 1)).isoformat()
    return start, end


def _upsert_prices(
    db_path: str, code: str, currency: str, rows: Iterable[tuple[str, float]], source: str
) -> int:
    n = 0
    with connect(db_path) as conn:
        ensure_schema(conn)
        for d, close in rows:
            conn.execute(
                """
                INSERT INTO prices_eod(code, date, close, currency, source)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(code, date, currency) DO UPDATE SET
                    close=excluded.close,
                    source=COALESCE(excluded.source, prices_eod.source),
                    fetched_at=CURRENT_TIMESTAMP
                """,
                (code, d, float(close), currency, source),
            )
            n += 1
        conn.commit()
    return n


def _upsert_fx(db_path: str, rows: Iterable[tuple[str, float]], source: str) -> int:
    n = 0
    with connect(db_path) as conn:
        ensure_schema(conn)
        for d, rate in rows:
            conn.execute(
                """
                INSERT INTO fx_rates(from_currency, to_currency, date, rate, source)
                VALUES('USD', 'CNY', ?, ?, ?)
                ON CONFLICT(from_currency, to_currency, date) DO UPDATE SET
                    rate=excluded.rate,
                    source=COALESCE(excluded.source, fx_rates.source),
                    fetched_at=CURRENT_TIMESTAMP
                """,
                (d, float(rate), source),
            )
            n += 1
        conn.commit()
    return n


def _fetch_symbol_eod(symbol: Symbol, start: str, end: str) -> list[tuple[str, float]]:
    market = symbol.market or infer_market_currency(symbol.code)[0]
    if market == "CN":
        return fetch_cn(code=symbol.code, start=start, end=end)
    return fetch_us(symbol=symbol.code, start=start, end=end)


def backfill(db_path: str, start: str, end: str, symbols: list[str] | None = None) -> IngestionStats:
    sym_list = load_active_symbols(db_path=db_path, explicit=symbols)
    prices_rows = 0
    for s in sym_list:
        currency = s.currency or infer_market_currency(s.code)[1]
        try:
            eod = _fetch_symbol_eod(s, start=start, end=end)
            src = "tencent_eod" if (s.market or infer_market_currency(s.code)[0]) == "CN" else "yahoo_eod"
            prices_rows += _upsert_prices(db_path=db_path, code=s.code, currency=currency, rows=eod, source=src)
        except (URLError, HTTPError, ValueError) as e:
            print(f"采集失败: {s.code} {e}")

    fx_rows = 0
    try:
        fx = fetch_usd_cny_timeseries(start=start, end=end)
        fx_rows = _upsert_fx(db_path=db_path, rows=fx, source="exchangerate_host")
    except (URLError, HTTPError, ValueError):
        fx_rows = 0

    stats = IngestionStats(symbols=len(sym_list), prices_rows=prices_rows, fx_rows=fx_rows)
    print(f"回填完成: symbols={stats.symbols}, prices={stats.prices_rows}, fx={stats.fx_rows}")
    return stats


def daily_sync(db_path: str, lookback_days: int = 7, symbols: list[str] | None = None) -> IngestionStats:
    start, end = _date_range_for_sync(lookback_days=lookback_days)
    stats = backfill(db_path=db_path, start=start, end=end, symbols=symbols)
    print(f"日更同步完成: start={start}, end={end}")
    return stats
