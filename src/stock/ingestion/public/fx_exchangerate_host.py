from __future__ import annotations

from stock.ingestion.http import get_json


def fetch_usd_cny_timeseries(start: str, end: str) -> list[tuple[str, float]]:
    url = "https://api.exchangerate.host/timeseries"
    params = {
        "base": "USD",
        "symbols": "CNY",
        "start_date": start,
        "end_date": end,
    }
    data = get_json(url=url, params=params, timeout=20)
    rates = data.get("rates") or {}
    out: list[tuple[str, float]] = []
    for d, payload in rates.items():
        cny = payload.get("CNY")
        if cny is None:
            continue
        out.append((d, float(cny)))
    out.sort(key=lambda x: x[0])
    return out


def fetch_usd_cny_latest() -> tuple[str, float] | None:
    url = "https://api.exchangerate.host/latest"
    params = {"base": "USD", "symbols": "CNY"}
    data = get_json(url=url, params=params, timeout=20)
    d = data.get("date")
    rate = (data.get("rates") or {}).get("CNY")
    if not d or rate is None:
        return None
    return str(d), float(rate)
