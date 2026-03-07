from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_type

from stock import db as dbm
from stock.holdings import HoldingPosition


@dataclass(frozen=True)
class ValuePoint:
    value_cny: float | None
    close_price: float | None
    exchange_rate: float | None


@dataclass(frozen=True)
class ReportRow:
    asset_id: str
    asset_class: str
    currency: str
    quantity: float
    avg_cost: float | None
    close_price: float | None
    value_cny: float | None
    delta_vs_prev_cny: float | None
    delta_vs_prev_pct: float | None
    delta_vs_year_start_cny: float | None
    delta_vs_year_start_pct: float | None
    asset_name: str | None = None


@dataclass(frozen=True)
class DailyReportData:
    report_date: str
    total_value_cny: float | None
    total_value_prev_day_cny: float | None
    delta_total_vs_prev_day_cny: float | None
    delta_total_vs_prev_day_pct: float | None
    total_value_year_start_cny: float | None
    delta_total_vs_year_start_cny: float | None
    delta_total_vs_year_start_pct: float | None
    rows: list[ReportRow]
    missing_prices: list[str]
    missing_fx: list[str]


_ASSET_CLASS_ORDER = {
    dbm.ASSET_CLASS_CN: 0,
    dbm.ASSET_CLASS_US: 1,
    dbm.ASSET_CLASS_CRYPTO: 2,
}


def _pct(delta: float, base: float) -> float | None:
    if base == 0:
        return None
    return delta / base


def _calc_for_date(
    conn: dbm.sqlite3.Connection,
    *,
    positions: list[HoldingPosition],
    target_date: str,
) -> tuple[dict[str, ValuePoint], float | None, list[str], list[str]]:
    by_class: dict[str, list[str]] = {dbm.ASSET_CLASS_CN: [], dbm.ASSET_CLASS_US: [], dbm.ASSET_CLASS_CRYPTO: []}
    for p in positions:
        by_class.setdefault(p.asset_class, []).append(p.asset_id)

    prices_cn = dbm.get_prices_for_date(conn, asset_class=dbm.ASSET_CLASS_CN, asset_ids=by_class[dbm.ASSET_CLASS_CN], price_date=target_date)
    prices_us = dbm.get_prices_for_date(conn, asset_class=dbm.ASSET_CLASS_US, asset_ids=by_class[dbm.ASSET_CLASS_US], price_date=target_date)
    prices_crypto = dbm.get_prices_for_date(conn, asset_class=dbm.ASSET_CLASS_CRYPTO, asset_ids=by_class[dbm.ASSET_CLASS_CRYPTO], price_date=target_date)
    fx_usd_cny = dbm.get_exchange_rate(conn, from_ccy="USD", to_ccy="CNY", rate_date=target_date)

    missing_prices: list[str] = []
    missing_fx: list[str] = []
    points: dict[str, ValuePoint] = {}
    total: float = 0.0
    any_value = False

    for p in positions:
        close: float | None
        if p.asset_class == dbm.ASSET_CLASS_CN:
            close = prices_cn.get(p.asset_id)
        elif p.asset_class == dbm.ASSET_CLASS_US:
            close = prices_us.get(p.asset_id)
        else:
            close = prices_crypto.get(p.asset_id)

        if close is None:
            missing_prices.append(p.asset_id)
            points[p.asset_id] = ValuePoint(value_cny=None, close_price=None, exchange_rate=fx_usd_cny)
            continue

        if p.currency == "CNY":
            value = p.quantity * close
            total += value
            any_value = True
            points[p.asset_id] = ValuePoint(value_cny=value, close_price=close, exchange_rate=None)
            continue

        if p.currency == "USD":
            if fx_usd_cny is None:
                missing_fx.append(p.asset_id)
                points[p.asset_id] = ValuePoint(value_cny=None, close_price=close, exchange_rate=None)
                continue
            value = p.quantity * close * fx_usd_cny
            total += value
            any_value = True
            points[p.asset_id] = ValuePoint(value_cny=value, close_price=close, exchange_rate=fx_usd_cny)
            continue

        missing_fx.append(p.asset_id)
        points[p.asset_id] = ValuePoint(value_cny=None, close_price=close, exchange_rate=None)

    return points, (total if any_value else None), missing_prices, missing_fx


def infer_report_date(conn: dbm.sqlite3.Connection, positions: list[HoldingPosition]) -> str | None:
    dates: list[str] = []
    for cls in (dbm.ASSET_CLASS_CN, dbm.ASSET_CLASS_US, dbm.ASSET_CLASS_CRYPTO):
        ids = [p.asset_id for p in positions if p.asset_class == cls]
        if not ids:
            continue
        ds = dbm.list_price_dates(conn, asset_class=cls, asset_ids=ids)
        if ds:
            dates.append(max(ds))
    if not dates:
        return None
    return max(dates)


def _candidate_dates(
    conn: dbm.sqlite3.Connection,
    *,
    positions: list[HoldingPosition],
    start_date: str | None,
    end_date: str | None,
) -> list[str]:
    s: set[str] = set()
    for cls in (dbm.ASSET_CLASS_CN, dbm.ASSET_CLASS_US, dbm.ASSET_CLASS_CRYPTO):
        ids = [p.asset_id for p in positions if p.asset_class == cls]
        if not ids:
            continue
        s |= dbm.list_price_dates(conn, asset_class=cls, asset_ids=ids, start_date=start_date, end_date=end_date)
    return sorted(s)


def select_prev_day(conn: dbm.sqlite3.Connection, *, positions: list[HoldingPosition], report_date: str) -> str | None:
    candidates = _candidate_dates(conn, positions=positions, start_date=None, end_date=None)
    for d in reversed(candidates):
        if d >= report_date:
            continue
        _, total, _, _ = _calc_for_date(conn, positions=positions, target_date=d)
        if total is not None:
            return d
    return None


def select_year_start(conn: dbm.sqlite3.Connection, *, positions: list[HoldingPosition], report_date: str) -> str | None:
    year = int(report_date.split("-", 1)[0])
    start = date_type(year=year, month=1, day=1).isoformat()
    candidates = _candidate_dates(conn, positions=positions, start_date=start, end_date=report_date)
    for d in candidates:
        if d > report_date:
            continue
        _, total, _, _ = _calc_for_date(conn, positions=positions, target_date=d)
        if total is not None:
            return d
    return None


def build_daily_report_data(
    conn: dbm.sqlite3.Connection,
    *,
    positions: list[HoldingPosition],
    report_date: str,
) -> DailyReportData:
    points_today, total_today, missing_prices, missing_fx = _calc_for_date(conn, positions=positions, target_date=report_date)

    prev_day = select_prev_day(conn, positions=positions, report_date=report_date)
    year_start = select_year_start(conn, positions=positions, report_date=report_date)

    total_prev: float | None = None
    total_year: float | None = None
    points_prev: dict[str, ValuePoint] = {}
    points_year: dict[str, ValuePoint] = {}

    if prev_day is not None:
        points_prev, total_prev, _, _ = _calc_for_date(conn, positions=positions, target_date=prev_day)
    if year_start is not None:
        points_year, total_year, _, _ = _calc_for_date(conn, positions=positions, target_date=year_start)

    def delta_pair(cur: float | None, base: float | None) -> tuple[float | None, float | None]:
        if cur is None or base is None:
            return None, None
        d = cur - base
        return d, _pct(d, base)

    delta_total_prev, delta_total_prev_pct = delta_pair(total_today, total_prev)
    delta_total_year, delta_total_year_pct = delta_pair(total_today, total_year)

    def sorted_positions() -> list[HoldingPosition]:
        return sorted(positions, key=lambda p: (_ASSET_CLASS_ORDER.get(p.asset_class, 99), p.asset_id))

    rows: list[ReportRow] = []
    for p in sorted_positions():
        pt = points_today.get(p.asset_id) or ValuePoint(None, None, None)
        pv = points_prev.get(p.asset_id) if prev_day else None
        py = points_year.get(p.asset_id) if year_start else None

        dv_prev, dv_prev_pct = delta_pair(pt.value_cny, pv.value_cny if pv else None)
        dv_year, dv_year_pct = delta_pair(pt.value_cny, py.value_cny if py else None)

        rows.append(
            ReportRow(
                asset_id=p.asset_id,
                asset_class=p.asset_class,
                currency=p.currency,
                quantity=p.quantity,
                avg_cost=p.avg_cost,
                close_price=pt.close_price,
                value_cny=pt.value_cny,
                delta_vs_prev_cny=dv_prev,
                delta_vs_prev_pct=dv_prev_pct,
                delta_vs_year_start_cny=dv_year,
                delta_vs_year_start_pct=dv_year_pct,
                asset_name=p.name,
            )
        )

    return DailyReportData(
        report_date=report_date,
        total_value_cny=total_today,
        total_value_prev_day_cny=total_prev,
        delta_total_vs_prev_day_cny=delta_total_prev,
        delta_total_vs_prev_day_pct=delta_total_prev_pct,
        total_value_year_start_cny=total_year,
        delta_total_vs_year_start_cny=delta_total_year,
        delta_total_vs_year_start_pct=delta_total_year_pct,
        rows=rows,
        missing_prices=sorted(set(missing_prices)),
        missing_fx=sorted(set(missing_fx)),
    )

