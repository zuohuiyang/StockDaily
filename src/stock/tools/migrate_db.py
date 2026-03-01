from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from stock.db.connect import connect
from stock.db.schema import ensure_schema


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table,)
    ).fetchone()
    return row is not None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


def migrate(target_db: str, source_dbs: Iterable[str]) -> None:
    target_path = Path(target_db)
    with connect(str(target_path)) as conn:
        ensure_schema(conn)

    stats: dict[str, int] = {
        "sources_seen": 0,
        "symbols_upserted": 0,
        "prices_upserted": 0,
        "fx_upserted": 0,
    }

    with connect(str(target_path)) as target:
        for source_db in source_dbs:
            source_path = Path(source_db)
            if not source_path.exists():
                continue

            stats["sources_seen"] += 1
            source = sqlite3.connect(str(source_path))

            try:
                if _table_exists(source, "holdings"):
                    cols = _columns(source, "holdings")
                    select_cols = []
                    if "code" in cols:
                        select_cols.append("code")
                    if "name" in cols:
                        select_cols.append("name")
                    if "currency" in cols:
                        select_cols.append("currency")
                    if not select_cols or "code" not in select_cols:
                        select_cols = []

                    if select_cols:
                        rows = source.execute(
                            f"SELECT {', '.join(select_cols)} FROM holdings"
                        ).fetchall()
                        for r in rows:
                            code = r[select_cols.index("code")]
                            name = r[select_cols.index("name")] if "name" in select_cols else None
                            currency = (
                                r[select_cols.index("currency")] if "currency" in select_cols else None
                            )
                            target.execute(
                                """
                                INSERT INTO symbols(code, name, currency, active)
                                VALUES(?, ?, ?, 1)
                                ON CONFLICT(code) DO UPDATE SET
                                    name=COALESCE(excluded.name, symbols.name),
                                    currency=COALESCE(excluded.currency, symbols.currency),
                                    updated_at=CURRENT_TIMESTAMP
                                """,
                                (code, name, currency),
                            )
                            stats["symbols_upserted"] += 1

                if _table_exists(source, "stock_prices"):
                    cols = _columns(source, "stock_prices")
                    required = {"code", "price", "date"}
                    if required.issubset(cols):
                        currency_col = "currency" if "currency" in cols else None
                        source_col = "source" if "source" in cols else None

                        select_cols = ["code", "price", "date"]
                        if currency_col:
                            select_cols.append(currency_col)
                        if source_col:
                            select_cols.append(source_col)

                        rows = source.execute(
                            f"SELECT {', '.join(select_cols)} FROM stock_prices"
                        ).fetchall()

                        for r in rows:
                            code = r[select_cols.index("code")]
                            close = r[select_cols.index("price")]
                            date = r[select_cols.index("date")]
                            currency = (
                                r[select_cols.index(currency_col)]
                                if currency_col
                                else "CNY"
                            )
                            src = (
                                r[select_cols.index(source_col)]
                                if source_col
                                else str(source_path.name)
                            )

                            target.execute(
                                """
                                INSERT INTO prices_eod(code, date, close, currency, source)
                                VALUES(?, ?, ?, ?, ?)
                                ON CONFLICT(code, date, currency) DO UPDATE SET
                                    close=excluded.close,
                                    source=COALESCE(excluded.source, prices_eod.source),
                                    fetched_at=CURRENT_TIMESTAMP
                                """,
                                (code, date, close, currency, src),
                            )
                            stats["prices_upserted"] += 1

                if _table_exists(source, "exchange_rates"):
                    cols = _columns(source, "exchange_rates")
                    required = {"from_currency", "to_currency", "rate", "date"}
                    if required.issubset(cols):
                        rows = source.execute(
                            "SELECT from_currency, to_currency, rate, date FROM exchange_rates"
                        ).fetchall()

                        for from_ccy, to_ccy, rate, date in rows:
                            target.execute(
                                """
                                INSERT INTO fx_rates(from_currency, to_currency, date, rate, source)
                                VALUES(?, ?, ?, ?, ?)
                                ON CONFLICT(from_currency, to_currency, date) DO UPDATE SET
                                    rate=excluded.rate,
                                    source=COALESCE(excluded.source, fx_rates.source),
                                    fetched_at=CURRENT_TIMESTAMP
                                """,
                                (from_ccy, to_ccy, date, rate, str(source_path.name)),
                            )
                            stats["fx_upserted"] += 1
            finally:
                source.close()

        target.commit()

    lines = [
        "迁移完成：",
        f"- 发现源库数量: {stats['sources_seen']}",
        f"- 写入/更新 symbols: {stats['symbols_upserted']}",
        f"- 写入/更新 prices_eod: {stats['prices_upserted']}",
        f"- 写入/更新 fx_rates: {stats['fx_upserted']}",
    ]
    print("\n".join(lines))

