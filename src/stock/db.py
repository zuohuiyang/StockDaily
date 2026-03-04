from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from collections.abc import Iterable
from dataclasses import dataclass


ASSET_CLASS_CN = "CN_STOCK"
ASSET_CLASS_US = "US_STOCK"
ASSET_CLASS_CRYPTO = "CRYPTO"

TABLE_ASSETS = "assets"
TABLE_CN_PRICES = "cn_stock_prices_daily"
TABLE_US_PRICES = "us_stock_prices_daily"
TABLE_CRYPTO_PRICES = "crypto_prices_daily"
TABLE_EXCHANGE_RATES = "exchange_rates_daily"


@dataclass(frozen=True)
class AssetRow:
    asset_id: str
    asset_class: str
    quote_ccy: str
    name: str | None
    is_active: int


@contextmanager
def connect(db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
    finally:
        conn.close()


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE_ASSETS} (
            asset_id TEXT PRIMARY KEY,
            asset_class TEXT NOT NULL,
            quote_ccy TEXT NOT NULL,
            name TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_assets_active ON {TABLE_ASSETS}(is_active)")

    for table in (TABLE_CN_PRICES, TABLE_US_PRICES, TABLE_CRYPTO_PRICES):
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
                asset_id TEXT NOT NULL,
                price_date TEXT NOT NULL,
                close_price REAL NOT NULL,
                quote_ccy TEXT NOT NULL,
                source TEXT,
                fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (asset_id, price_date)
            )
            """
        )
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_date ON {table}(price_date)")

    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE_EXCHANGE_RATES} (
            from_ccy TEXT NOT NULL,
            to_ccy TEXT NOT NULL,
            rate_date TEXT NOT NULL,
            exchange_rate REAL NOT NULL,
            source TEXT,
            fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (from_ccy, to_ccy, rate_date)
        )
        """
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_exchange_date_pair ON {TABLE_EXCHANGE_RATES}(rate_date, from_ccy, to_ccy)"
    )
    conn.commit()


def table_for_asset_class(asset_class: str) -> str:
    if asset_class == ASSET_CLASS_CN:
        return TABLE_CN_PRICES
    if asset_class == ASSET_CLASS_US:
        return TABLE_US_PRICES
    if asset_class == ASSET_CLASS_CRYPTO:
        return TABLE_CRYPTO_PRICES
    raise ValueError(f"未知 asset_class: {asset_class}")


def upsert_asset(
    conn: sqlite3.Connection,
    *,
    asset_id: str,
    asset_class: str,
    quote_ccy: str,
    name: str | None = None,
    is_active: int = 1,
) -> None:
    conn.execute(
        f"""
        INSERT INTO {TABLE_ASSETS}(asset_id, asset_class, quote_ccy, name, is_active, updated_at)
        VALUES(?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(asset_id) DO UPDATE SET
            asset_class=excluded.asset_class,
            quote_ccy=excluded.quote_ccy,
            name=excluded.name,
            is_active=excluded.is_active,
            updated_at=CURRENT_TIMESTAMP
        """,
        (asset_id, asset_class, quote_ccy, name, int(is_active)),
    )


def get_active_assets(conn: sqlite3.Connection) -> list[AssetRow]:
    rows = conn.execute(
        f"SELECT asset_id, asset_class, quote_ccy, name, is_active FROM {TABLE_ASSETS} WHERE is_active=1 ORDER BY asset_id"
    ).fetchall()
    return [
        AssetRow(
            asset_id=str(r["asset_id"]),
            asset_class=str(r["asset_class"]),
            quote_ccy=str(r["quote_ccy"]),
            name=(str(r["name"]) if r["name"] is not None else None),
            is_active=int(r["is_active"]),
        )
        for r in rows
    ]


def upsert_daily_price(
    conn: sqlite3.Connection,
    *,
    asset_class: str,
    asset_id: str,
    price_date: str,
    close_price: float,
    quote_ccy: str,
    source: str | None,
) -> None:
    table = table_for_asset_class(asset_class)
    conn.execute(
        f"""
        INSERT INTO {table}(asset_id, price_date, close_price, quote_ccy, source, fetched_at)
        VALUES(?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(asset_id, price_date) DO UPDATE SET
            close_price=excluded.close_price,
            quote_ccy=excluded.quote_ccy,
            source=excluded.source,
            fetched_at=CURRENT_TIMESTAMP
        """,
        (asset_id, price_date, float(close_price), quote_ccy, source),
    )


def upsert_exchange_rate(
    conn: sqlite3.Connection,
    *,
    from_ccy: str,
    to_ccy: str,
    rate_date: str,
    exchange_rate: float,
    source: str | None,
) -> None:
    conn.execute(
        f"""
        INSERT INTO {TABLE_EXCHANGE_RATES}(from_ccy, to_ccy, rate_date, exchange_rate, source, fetched_at)
        VALUES(?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(from_ccy, to_ccy, rate_date) DO UPDATE SET
            exchange_rate=excluded.exchange_rate,
            source=excluded.source,
            fetched_at=CURRENT_TIMESTAMP
        """,
        (from_ccy, to_ccy, rate_date, float(exchange_rate), source),
    )


def get_exchange_rate(
    conn: sqlite3.Connection,
    *,
    from_ccy: str,
    to_ccy: str,
    rate_date: str,
) -> float | None:
    row = conn.execute(
        f"""
        SELECT exchange_rate FROM {TABLE_EXCHANGE_RATES}
        WHERE from_ccy=? AND to_ccy=? AND rate_date=?
        """,
        (from_ccy, to_ccy, rate_date),
    ).fetchone()
    if not row:
        return None
    return float(row["exchange_rate"])


def get_prices_for_date(
    conn: sqlite3.Connection,
    *,
    asset_class: str,
    asset_ids: Iterable[str],
    price_date: str,
) -> dict[str, float]:
    ids = [str(x) for x in asset_ids]
    if not ids:
        return {}
    table = table_for_asset_class(asset_class)
    ph = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"""
        SELECT asset_id, close_price FROM {table}
        WHERE price_date=? AND asset_id IN ({ph})
        """,
        (price_date, *ids),
    ).fetchall()
    return {str(r["asset_id"]): float(r["close_price"]) for r in rows}


def list_price_dates(
    conn: sqlite3.Connection,
    *,
    asset_class: str,
    asset_ids: Iterable[str],
    start_date: str | None = None,
    end_date: str | None = None,
) -> set[str]:
    ids = [str(x) for x in asset_ids]
    if not ids:
        return set()
    table = table_for_asset_class(asset_class)
    ph = ",".join("?" for _ in ids)
    clauses = ["asset_id IN (" + ph + ")"]
    params: list[object] = list(ids)
    if start_date is not None:
        clauses.append("price_date >= ?")
        params.append(start_date)
    if end_date is not None:
        clauses.append("price_date <= ?")
        params.append(end_date)
    where = " AND ".join(clauses)
    rows = conn.execute(f"SELECT DISTINCT price_date FROM {table} WHERE {where}", params).fetchall()
    return {str(r["price_date"]) for r in rows}


def get_latest_price_date(conn: sqlite3.Connection) -> str | None:
    dates: list[str] = []
    for table in (TABLE_CN_PRICES, TABLE_US_PRICES, TABLE_CRYPTO_PRICES):
        row = conn.execute(f"SELECT MAX(price_date) AS max_date FROM {table}").fetchone()
        if row and row["max_date"]:
            dates.append(str(row["max_date"]))
    if not dates:
        return None
    return max(dates)
