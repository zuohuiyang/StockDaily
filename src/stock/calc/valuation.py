from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from stock.calc.positions import Position
from stock.db.connect import connect
from stock.db.schema import ensure_schema


@dataclass(frozen=True)
class ValuedPosition:
    code: str
    currency: str
    quantity: float
    close: float | None
    avg_cost: float | None
    market_value_cny: float | None
    unrealized_pnl_cny: float | None
    realized_pnl_cny: float | None


def get_latest_price_date(db_path: str) -> str | None:
    with connect(db_path) as conn:
        ensure_schema(conn)
        row = conn.execute("SELECT MAX(date) AS d FROM prices_eod").fetchone()
        return row["d"] if row and row["d"] else None


def load_prices_for_date(db_path: str, target_date: str) -> dict[str, dict]:
    with connect(db_path) as conn:
        ensure_schema(conn)
        rows = conn.execute(
            "SELECT code, close, currency FROM prices_eod WHERE date = ?", (target_date,)
        ).fetchall()
    return {r["code"]: {"close": float(r["close"]), "currency": r["currency"]} for r in rows}


def load_usd_cny_rate(db_path: str, target_date: str) -> float | None:
    with connect(db_path) as conn:
        ensure_schema(conn)
        row = conn.execute(
            """
            SELECT rate FROM fx_rates
            WHERE from_currency='USD' AND to_currency='CNY' AND date <= ?
            ORDER BY date DESC LIMIT 1
            """,
            (target_date,),
        ).fetchone()
    return float(row["rate"]) if row else None


def _to_cny(value: float, currency: str, usd_cny: float | None) -> float | None:
    if currency == "CNY":
        return value
    if currency == "USD" and usd_cny is not None:
        return value * usd_cny
    return None


def value_positions(
    positions: Mapping[str, Position], prices: Mapping[str, dict], usd_cny: float | None
) -> tuple[list[ValuedPosition], list[str]]:
    valued: list[ValuedPosition] = []
    missing: list[str] = []

    for code, pos in positions.items():
        price_row = prices.get(code)
        close = float(price_row["close"]) if price_row else None
        currency = pos.currency

        avg_cost = pos.avg_cost
        if close is None:
            missing.append(code)
            valued.append(
                ValuedPosition(
                    code=code,
                    currency=currency,
                    quantity=pos.quantity,
                    close=None,
                    avg_cost=avg_cost,
                    market_value_cny=None,
                    unrealized_pnl_cny=None,
                    realized_pnl_cny=_to_cny(pos.realized_pnl, currency, usd_cny),
                )
            )
            continue

        market_value_local = pos.quantity * close
        market_value_cny = _to_cny(market_value_local, currency, usd_cny)

        unrealized_local = None
        unrealized_cny = None
        if avg_cost is not None:
            unrealized_local = (close - avg_cost) * pos.quantity
            unrealized_cny = _to_cny(unrealized_local, currency, usd_cny)

        valued.append(
            ValuedPosition(
                code=code,
                currency=currency,
                quantity=pos.quantity,
                close=close,
                avg_cost=avg_cost,
                market_value_cny=market_value_cny,
                unrealized_pnl_cny=unrealized_cny,
                realized_pnl_cny=_to_cny(pos.realized_pnl, currency, usd_cny),
            )
        )

    valued.sort(key=lambda x: (x.currency, x.code))
    return valued, missing

