from __future__ import annotations

import os
from pathlib import Path

from stock.calc import DailyReportData, ReportRow


def _fmt_num(v: float) -> str:
    return f"{v:.2f}"


def _fmt_pct(v: float) -> str:
    return f"{v*100:.2f}%"


def _norm_signed(v: float) -> float:
    if abs(v) < 0.0005:
        return 0.0
    return v


def _fmt_signed_num(v: float) -> str:
    return f"{_norm_signed(v):+.2f}"


def _fmt_signed_pct(v: float) -> str:
    return f"{_norm_signed(v*100):+.2f}%"


def _fmt_money_delta(delta: float | None, pct: float | None) -> str:
    if delta is None or pct is None:
        return "-"
    return f"{_fmt_signed_num(delta)}（{_fmt_signed_pct(pct)}）"


def _fmt_value(v: float | None) -> str:
    if v is None:
        return "-"
    return _fmt_num(v)


def _fmt_row(r: ReportRow) -> str:
    asset_display = f"{r.asset_name}({r.asset_id})" if r.asset_name else r.asset_id
    return (
        f"| {asset_display} | {r.asset_class} | {r.currency} | {_fmt_num(r.quantity)} | {_fmt_value(r.avg_cost)}"
        f" | {_fmt_value(r.close_price)} | {_fmt_value(r.value_cny)}"
        f" | {_fmt_money_delta(r.delta_vs_prev_cny, r.delta_vs_prev_pct)}"
        f" | {_fmt_money_delta(r.delta_vs_year_start_cny, r.delta_vs_year_start_pct)} |"
    )


def render_markdown(data: DailyReportData) -> str:
    missing_prices = "无" if not data.missing_prices else ", ".join(data.missing_prices)
    missing_fx = "无" if not data.missing_fx else ", ".join(data.missing_fx)

    lines: list[str] = []
    lines.append("# StockDaily 日报")
    lines.append("")
    lines.append(f"- 报告日期：{data.report_date}")
    lines.append("")
    lines.append("## 资产概览")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|---|---:|")
    lines.append(f"| 总资产（CNY） | {_fmt_value(data.total_value_cny)} |")
    lines.append(f"| 昨日总资产（CNY） | {_fmt_value(data.total_value_prev_day_cny)} |")
    lines.append(
        f"| 较昨日（CNY） | {_fmt_money_delta(data.delta_total_vs_prev_day_cny, data.delta_total_vs_prev_day_pct)} |"
    )
    lines.append(f"| 年初总资产（CNY） | {_fmt_value(data.total_value_year_start_cny)} |")
    lines.append(
        f"| 较年初（CNY） | {_fmt_money_delta(data.delta_total_vs_year_start_cny, data.delta_total_vs_year_start_pct)} |"
    )
    lines.append("")
    lines.append("## 持仓明细")
    lines.append("")
    lines.append("| 标的 | 类型 | 币种 | 数量 | 成本价 | 收盘价 | 市值（CNY） | 较昨日（CNY） | 较年初（CNY） |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|")
    for r in data.rows:
        lines.append(_fmt_row(r))
    lines.append("")
    lines.append("## 数据缺口")
    lines.append("")
    lines.append(f"- 缺少收盘价：{missing_prices}")
    lines.append(f"- 缺少汇率：{missing_fx}")
    lines.append("")
    return "\n".join(lines)


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    os.replace(tmp, path)


def write_daily_report(
    *,
    out_dir: str,
    report_date: str,
    markdown: str,
    latest_name: str | None,
) -> Path:
    out = Path(out_dir)
    archive = out / f"{report_date}_report.md"
    atomic_write_text(archive, markdown)
    if latest_name:
        latest = out / latest_name
        atomic_write_text(latest, markdown)
    return archive
