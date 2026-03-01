from __future__ import annotations

import json
from datetime import date

from stock.ingestion.http import get_text


def fetch_close_prices(code: str, start: str, end: str) -> list[tuple[str, float]]:
    market = "sz" if code.startswith(("0", "3")) else "sh"
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {
        "_var": "kline_dayqfq",
        "param": f"{market}{code},day,{start},{end},640,qfq",
        "r": "0.123456789",
    }
    text = get_text(url=url, params=params, timeout=20).strip()
    prefix = "kline_dayqfq="
    if text.startswith(prefix):
        text = text[len(prefix) :]
    if text.endswith(";"):
        text = text[:-1]
    data = json.loads(text)
    key = f"{market}{code}"
    day = data.get("data", {}).get(key, {}).get("day") or []
    out: list[tuple[str, float]] = []
    for row in day:
        d = row[0]
        close = float(row[2])
        out.append((d, close))
    return out


def fetch_close_prices_last_days(code: str, days: int = 14) -> list[tuple[str, float]]:
    end = date.today().isoformat()
    start = (date.today().toordinal() - days)
    start_date = date.fromordinal(start).isoformat()
    return fetch_close_prices(code=code, start=start_date, end=end)
