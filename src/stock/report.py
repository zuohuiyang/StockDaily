import argparse
import sys

from stock.db.connect import connect
from stock.db.schema import ensure_schema


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m stock.report")
    parser.add_argument("--db", default="portfolio.db")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("daily")
    p.add_argument("--date", default=None)
    p.add_argument("--out-dir", default="daily_reports")
    p.add_argument("--latest-name", default="latest_report.md")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    with connect(args.db) as conn:
        ensure_schema(conn)

    if args.cmd == "daily":
        from stock.delivery.daily_report import generate_daily_report

        try:
            out_path = generate_daily_report(
                db_path=args.db, target_date=args.date, out_dir=args.out_dir, latest_name=args.latest_name
            )
            print(str(out_path))
            return 0
        except Exception as e:
            print(f"生成日报失败: {e}", file=sys.stderr)
            return 1

    print(f"Unknown command: {args.cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

