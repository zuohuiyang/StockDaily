from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date as date_type
from datetime import datetime, timezone

from stock.http import get_json, get_text


def fetch_cn_close_prices(asset_id: str, start: str, end: str) -> list[tuple[str, float]]:
    market = "sz" if asset_id.startswith(("0", "3")) else "sh"
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {
        "_var": "kline_dayqfq",
        "param": f"{market}{asset_id},day,{start},{end},640,qfq",
        "r": "0.123456789",
    }
    text = get_text(url=url, params=params, timeout=20).strip()
    prefix = "kline_dayqfq="
    if text.startswith(prefix):
        text = text[len(prefix) :]
    if text.endswith(";"):
        text = text[:-1]
    data = json.loads(text)
    key = f"{market}{asset_id}"
    payload = data.get("data", {}).get(key, {}) or {}
    day = payload.get("qfqday") or payload.get("day") or []
    out: list[tuple[str, float]] = []
    for row in day:
        d = row[0]
        close = float(row[2])
        out.append((d, close))
    return out


def _to_ts_utc(d: str) -> int:
    dt = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def fetch_us_close_prices(asset_id: str, start: str, end: str) -> list[tuple[str, float]]:
    sym = asset_id.lower()
    if not sym.endswith(".us"):
        sym = f"{sym}.us"
    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
    text = get_text(url=url, timeout=20)
    reader = csv.DictReader(text.splitlines())
    out: list[tuple[str, float]] = []
    for row in reader:
        d = row.get("Date")
        c = row.get("Close")
        if not d or not c or c == "null":
            continue
        if d < start or d > end:
            continue
        out.append((d, float(c)))
    return out


def fetch_usd_cny_timeseries(start: str, end: str) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []

    url = "https://api.exchangerate.host/timeseries"
    params = {"base": "USD", "symbols": "CNY", "start_date": start, "end_date": end}
    try:
        data = get_json(url=url, params=params, timeout=20)
        rates = data.get("rates") or {}
        for d, payload in rates.items():
            cny = (payload or {}).get("CNY")
            if cny is None:
                continue
            out.append((str(d), float(cny)))
    except Exception:
        out = []

    if out:
        out.sort(key=lambda x: x[0])
        return out

    url = f"https://api.frankfurter.app/{start}..{end}"
    params = {"from": "USD", "to": "CNY"}
    data = get_json(url=url, params=params, timeout=20)
    rates = data.get("rates") or {}
    for d, payload in rates.items():
        cny = (payload or {}).get("CNY")
        if cny is None:
            continue
        out.append((str(d), float(cny)))
    out.sort(key=lambda x: x[0])
    return out


_COINGECKO_ID_BY_SYMBOL = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
}


def fetch_crypto_close_prices_usd(asset_id: str, start: str, end: str) -> list[tuple[str, float]]:
    coin_id = _COINGECKO_ID_BY_SYMBOL.get(asset_id.upper())
    if not coin_id:
        return []
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"
    start_ts = _to_ts_utc(start)
    end_ts = _to_ts_utc(end) + 86400
    params = {"vs_currency": "usd", "from": str(start_ts), "to": str(end_ts)}
    data = get_json(url=url, params=params, timeout=20)
    prices = data.get("prices") or []
    by_day: dict[str, list[float]] = defaultdict(list)
    for ts_ms, price in prices:
        if price is None:
            continue
        d = datetime.fromtimestamp(int(ts_ms) / 1000.0, tz=timezone.utc).date().isoformat()
        by_day[d].append(float(price))
    out: list[tuple[str, float]] = []
    for d, ps in by_day.items():
        if not ps:
            continue
        out.append((d, ps[-1]))
    out.sort(key=lambda x: x[0])
    return out


def yesterday() -> str:
    return date_type.fromordinal(date_type.today().toordinal() - 1).isoformat()
