from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Iterable

from stock.db.connect import connect
from stock.db.schema import ensure_schema


@dataclass(frozen=True)
class Symbol:
    code: str
    market: str | None
    currency: str | None
    name: str | None


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table,)
    ).fetchone()
    return row is not None


def infer_market_currency(code: str) -> tuple[str, str]:
    if code.isdigit() and len(code) == 6:
        return "CN", "CNY"
    return "US", "USD"


def load_active_symbols(db_path: str, explicit: Iterable[str] | None = None) -> list[Symbol]:
    explicit_list = [s.strip() for s in (explicit or []) if s and s.strip()]

    with connect(db_path) as conn:
        ensure_schema(conn)

        if explicit_list:
            symbols = []
            for code in explicit_list:
                market, currency = infer_market_currency(code)
                row = conn.execute("SELECT name FROM symbols WHERE code=?", (code,)).fetchone()
                name = row["name"] if row else None
                symbols.append(Symbol(code=code, market=market, currency=currency, name=name))
            return symbols

        rows = conn.execute("SELECT code, market, currency, name FROM symbols WHERE active=1").fetchall()
        if rows:
            return [
                Symbol(code=r["code"], market=r["market"], currency=r["currency"], name=r["name"])
                for r in rows
            ]

        if _table_exists(conn, "holdings"):
            hrows = conn.execute("SELECT code, name, currency FROM holdings").fetchall()
            symbols = []
            for r in hrows:
                code = r["code"]
                name = r["name"] if "name" in r.keys() else None
                currency = r["currency"] if "currency" in r.keys() else None
                market, inferred_currency = infer_market_currency(code)
                final_currency = currency or inferred_currency
                conn.execute(
                    """
                    INSERT INTO symbols(code, market, currency, name, active)
                    VALUES(?, ?, ?, ?, 1)
                    ON CONFLICT(code) DO UPDATE SET
                        market=COALESCE(excluded.market, symbols.market),
                        currency=COALESCE(excluded.currency, symbols.currency),
                        name=COALESCE(excluded.name, symbols.name),
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (code, market, final_currency, name),
                )
                symbols.append(Symbol(code=code, market=market, currency=final_currency, name=name))
            conn.commit()
            return symbols

        raise RuntimeError("未找到 symbols 或 holdings，无法确定采集标的列表")

