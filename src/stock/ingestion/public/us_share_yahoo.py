from __future__ import annotations

from datetime import datetime, timezone

from stock.ingestion.http import get_json


def _to_ts(d: str) -> int:
    dt = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def fetch_close_prices(symbol: str, start: str, end: str) -> list[tuple[str, float]]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {
        "period1": _to_ts(start),
        "period2": _to_ts(end) + 86400,
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    }
    data = get_json(url=url, params=params, timeout=20)
    result = (data.get("chart") or {}).get("result") or []
    if not result:
        return []
    r0 = result[0]
    ts = r0.get("timestamp") or []
    indicators = (r0.get("indicators") or {}).get("quote") or []
    closes = indicators[0].get("close") if indicators else None
    if not closes:
        return []
    out: list[tuple[str, float]] = []
    for t, c in zip(ts, closes, strict=False):
        if c is None:
            continue
        d = datetime.fromtimestamp(int(t), tz=timezone.utc).date().isoformat()
        out.append((d, float(c)))
    return out
