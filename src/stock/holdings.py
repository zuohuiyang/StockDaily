from __future__ import annotations

import json
import re
from dataclasses import dataclass

from stock import db as dbm


@dataclass(frozen=True)
class HoldingPosition:
    asset_class: str
    asset_id: str
    quantity: float
    currency: str
    avg_cost: float | None
    name: str | None = None


_CN_CODE_RE = re.compile(r"^\d{6}$")


def infer_asset_class(asset_id: str) -> str:
    up = asset_id.upper()
    if up in ("BTC", "ETH"):
        return dbm.ASSET_CLASS_CRYPTO
    if _CN_CODE_RE.match(asset_id):
        return dbm.ASSET_CLASS_CN
    return dbm.ASSET_CLASS_US


def infer_currency(asset_class: str) -> str:
    if asset_class == dbm.ASSET_CLASS_CN:
        return "CNY"
    return "USD"


def parse_position_arg(s: str) -> HoldingPosition:
    if ":" not in s:
        raise ValueError(f"--position 格式错误: {s}（应为 asset_id:quantity）")
    asset_id, qty = s.split(":", 1)
    asset_id = asset_id.strip()
    qty = qty.strip()
    if not asset_id:
        raise ValueError(f"--position 格式错误: {s}（asset_id 为空）")
    try:
        quantity = float(qty)
    except ValueError:
        raise ValueError(f"--position 格式错误: {s}（quantity 不是数字）") from None
    asset_class = infer_asset_class(asset_id)
    norm_id = asset_id if asset_class == dbm.ASSET_CLASS_CN else asset_id.upper()
    return HoldingPosition(
        asset_class=asset_class,
        asset_id=norm_id,
        quantity=quantity,
        currency=infer_currency(asset_class),
        avg_cost=None,
    )


def load_holdings_json(path: str) -> list[HoldingPosition]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    positions = data.get("positions")
    if not isinstance(positions, list):
        raise ValueError("持仓账本 JSON 缺少 positions 数组")
    out: list[HoldingPosition] = []
    for i, p in enumerate(positions):
        if not isinstance(p, dict):
            raise ValueError(f"positions[{i}] 不是对象")
        missing: list[str] = []
        asset_class = p.get("asset_class")
        asset_id = p.get("asset_id")
        quantity = p.get("quantity")
        currency = p.get("currency")
        avg_cost = p.get("avg_cost")
        name = p.get("name")
        if not asset_class:
            missing.append("asset_class")
        if not asset_id:
            missing.append("asset_id")
        if quantity is None:
            missing.append("quantity")
        if not currency:
            missing.append("currency")
        if missing:
            raise ValueError(f"positions[{i}] 缺少字段: {', '.join(missing)}")
        try:
            q = float(quantity)
        except ValueError:
            raise ValueError(f"positions[{i}].quantity 不是数字") from None
        c = str(currency).upper()
        cls = str(asset_class)
        aid = str(asset_id).strip()
        if not aid:
            raise ValueError(f"positions[{i}].asset_id 为空")
        if cls != dbm.ASSET_CLASS_CN:
            aid = aid.upper()
        if avg_cost is None:
            ac = None
        else:
            try:
                ac = float(avg_cost)
            except ValueError:
                raise ValueError(f"positions[{i}].avg_cost 不是数字") from None
        out.append(
            HoldingPosition(
                asset_class=cls,
                asset_id=aid,
                quantity=q,
                currency=c,
                avg_cost=ac,
                name=str(name) if name else None,
            )
        )
    return out
