from __future__ import annotations

from datetime import datetime
from pathlib import Path

from stock.calc.positions import Position, compute_positions_fifo, load_transactions
from stock.calc.valuation import get_latest_price_date, load_prices_for_date, load_usd_cny_rate, value_positions
from stock.db.connect import connect
from stock.db.schema import ensure_schema


def _fallback_positions_from_holdings(db_path: str) -> dict[str, Position]:
    with connect(db_path) as conn:
        ensure_schema(conn)
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='holdings' LIMIT 1"
        ).fetchone()
        if not row:
            return {}
        rows = conn.execute("SELECT code, quantity, currency FROM holdings").fetchall()
    out: dict[str, Position] = {}
    for r in rows:
        out[r["code"]] = Position(code=r["code"], currency=r["currency"], quantity=float(r["quantity"]), lots=[], realized_pnl=0.0)
    return out


def generate_daily_report(db_path: str, target_date: str | None, out_dir: str, latest_name: str) -> Path:
    if target_date is None:
        target_date = get_latest_price_date(db_path)
    if not target_date:
        raise RuntimeError("未找到 prices_eod 的可用日期，请先执行数据迁移或公网采集")

    txs = load_transactions(db_path=db_path, as_of_date=target_date)
    if txs:
        positions = compute_positions_fifo(txs)
    else:
        positions = _fallback_positions_from_holdings(db_path=db_path)

    prices = load_prices_for_date(db_path=db_path, target_date=target_date)
    usd_cny = load_usd_cny_rate(db_path=db_path, target_date=target_date)

    valued, missing = value_positions(positions=positions, prices=prices, usd_cny=usd_cny)

    total_value = sum(v.market_value_cny or 0 for v in valued)
    total_unrealized = sum(v.unrealized_pnl_cny or 0 for v in valued if v.unrealized_pnl_cny is not None)
    total_realized = sum(v.realized_pnl_cny or 0 for v in valued if v.realized_pnl_cny is not None)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fx_line = f"{usd_cny:.6f}" if usd_cny is not None else "缺失"

    lines: list[str] = []
    lines.append("# 📈 投资组合日报（收盘价）")
    lines.append("")
    lines.append(f"- 报告时间: {now}")
    lines.append(f"- 估值日期: {target_date}")
    lines.append(f"- USD/CNY: {fx_line}")
    lines.append("")
    lines.append("## 💰 汇总")
    lines.append("")
    lines.append(f"- 总资产（CNY）: {total_value:,.2f}")
    lines.append(f"- 未实现盈亏（CNY）: {total_unrealized:,.2f}")
    lines.append(f"- 已实现盈亏（CNY）: {total_realized:,.2f}")
    lines.append("")
    lines.append("## 📋 持仓明细")
    lines.append("")
    lines.append("| 标的 | 币种 | 数量 | 成本均价 | 收盘价 | 市值(CNY) | 未实现盈亏(CNY) | 已实现盈亏(CNY) |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for v in valued:
        avg_cost = f"{v.avg_cost:.4f}" if v.avg_cost is not None else "-"
        close = f"{v.close:.4f}" if v.close is not None else "-"
        mv = f"{v.market_value_cny:,.2f}" if v.market_value_cny is not None else "-"
        upnl = f"{v.unrealized_pnl_cny:,.2f}" if v.unrealized_pnl_cny is not None else "-"
        rpnl = f"{v.realized_pnl_cny:,.2f}" if v.realized_pnl_cny is not None else "-"
        lines.append(f"| {v.code} | {v.currency} | {v.quantity:.4f} | {avg_cost} | {close} | {mv} | {upnl} | {rpnl} |")

    if missing:
        lines.append("")
        lines.append("## ⚠️ 数据缺口")
        lines.append("")
        lines.append("以下标的在估值日期缺少收盘价，未计入总资产：")
        for code in missing:
            lines.append(f"- {code}")

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    dated = out_path / f"{target_date}_report.md"
    latest = out_path / latest_name

    content = "\n".join(lines) + "\n"
    dated.write_text(content, encoding="utf-8")
    latest.write_text(content, encoding="utf-8")
    return dated
