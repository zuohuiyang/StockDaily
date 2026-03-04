from __future__ import annotations

import argparse
import sys

from stock import db as dbm
from stock.calc import build_daily_report_data, infer_report_date
from stock.holdings import load_holdings_json, parse_position_arg
from stock.reporting import render_markdown, write_daily_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m stock.report")
    parser.add_argument("--db", default="portfolio.db")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("daily")
    p.add_argument("--date", default=None)
    p.add_argument("--out-dir", default="daily_reports")
    p.add_argument("--latest-name", default="latest_report.md")
    p.add_argument("--holdings", default="private/holdings.json")
    p.add_argument("--position", action="append")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd != "daily":
        print(f"未知命令: {args.cmd}", file=sys.stderr)
        return 2

    try:
        positions = [parse_position_arg(s) for s in (args.position or [])]
        if not positions:
            positions = load_holdings_json(args.holdings)

        with dbm.connect(args.db) as conn:
            dbm.ensure_schema(conn)
            for p in positions:
                dbm.upsert_asset(
                    conn,
                    asset_id=p.asset_id,
                    asset_class=p.asset_class,
                    quote_ccy=p.currency,
                    is_active=1,
                )
            conn.commit()

            report_date = args.date or infer_report_date(conn, positions)
            if not report_date:
                raise ValueError("无法确定报告日期：数据库中没有可用的价格数据")

            data = build_daily_report_data(conn, positions=positions, report_date=report_date)

        md = render_markdown(data)
        out_path = write_daily_report(
            out_dir=args.out_dir,
            report_date=report_date,
            markdown=md,
            latest_name=args.latest_name,
        )
        print(str(out_path))
        return 0
    except Exception as e:
        print(f"生成日报失败: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
