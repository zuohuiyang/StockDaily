from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from stock.db.connect import connect
from stock.db.schema import ensure_schema


@dataclass
class Lot:
    quantity: float
    unit_cost: float


@dataclass
class Position:
    code: str
    currency: str
    quantity: float
    lots: list[Lot]
    realized_pnl: float

    @property
    def avg_cost(self) -> float | None:
        total_qty = sum(l.quantity for l in self.lots)
        if total_qty <= 0:
            return None
        total_cost = sum(l.quantity * l.unit_cost for l in self.lots)
        return total_cost / total_qty


def _parse_date(dt: str) -> str:
    try:
        return datetime.fromisoformat(dt.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return dt[:10]


def load_transactions(db_path: str, as_of_date: str) -> list[dict]:
    with connect(db_path) as conn:
        ensure_schema(conn)
        rows = conn.execute(
            """
            SELECT trade_time, code, side, quantity, price, currency, fee, fx_rate
            FROM transactions
            """
        ).fetchall()

    out = []
    for r in rows:
        d = _parse_date(r["trade_time"])
        if d <= as_of_date:
            out.append(
                {
                    "trade_time": r["trade_time"],
                    "code": r["code"],
                    "side": str(r["side"]).upper(),
                    "quantity": float(r["quantity"]),
                    "price": float(r["price"]),
                    "currency": r["currency"],
                    "fee": float(r["fee"] or 0),
                    "fx_rate": float(r["fx_rate"]) if r["fx_rate"] is not None else None,
                    "date": d,
                }
            )

    out.sort(key=lambda x: x["trade_time"])
    return out


def compute_positions_fifo(transactions: Iterable[dict]) -> dict[str, Position]:
    positions: dict[str, Position] = {}
    for tx in transactions:
        code = tx["code"]
        currency = tx["currency"]
        pos = positions.get(code)
        if pos is None:
            pos = Position(code=code, currency=currency, quantity=0.0, lots=[], realized_pnl=0.0)
            positions[code] = pos

        side = tx["side"]
        qty = float(tx["quantity"])
        price = float(tx["price"])
        fee = float(tx["fee"] or 0)

        if side == "BUY":
            unit_cost = (qty * price + fee) / qty if qty else price
            pos.lots.append(Lot(quantity=qty, unit_cost=unit_cost))
            pos.quantity += qty
        elif side == "SELL":
            remaining = qty
            proceeds = qty * price - fee
            cost = 0.0
            while remaining > 0 and pos.lots:
                lot = pos.lots[0]
                take = min(lot.quantity, remaining)
                cost += take * lot.unit_cost
                lot.quantity -= take
                remaining -= take
                pos.quantity -= take
                if lot.quantity <= 0:
                    pos.lots.pop(0)
            pos.realized_pnl += proceeds - cost
        else:
            continue

    return positions

