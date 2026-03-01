import argparse
import sys

from stock.db.connect import connect
from stock.db.schema import ensure_schema


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m stock.ingest")
    parser.add_argument("--db", default="portfolio.db")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("migrate-db")
    p.add_argument("--sources", nargs="*", default=["portfolio.db", "stock_tracker.db", "stock_portfolio.db"])

    p = sub.add_parser("public-backfill")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--symbols", nargs="*")

    p = sub.add_parser("public-daily")
    p.add_argument("--lookback-days", type=int, default=7)
    p.add_argument("--symbols", nargs="*")

    p = sub.add_parser("private-import")
    p.add_argument("--file", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    with connect(args.db) as conn:
        ensure_schema(conn)

    if args.cmd == "migrate-db":
        from stock.tools.migrate_db import migrate

        migrate(target_db=args.db, source_dbs=args.sources)
        return 0

    if args.cmd in ("public-backfill", "public-daily"):
        from stock.ingestion.public.sync import backfill, daily_sync

        if args.cmd == "public-backfill":
            backfill(db_path=args.db, start=args.start, end=args.end, symbols=args.symbols)
        else:
            daily_sync(db_path=args.db, lookback_days=args.lookback_days, symbols=args.symbols)
        return 0

    if args.cmd == "private-import":
        from stock.ingestion.private.transactions_import import import_transactions_csv

        import_transactions_csv(db_path=args.db, csv_path=args.file)
        return 0

    print(f"Unknown command: {args.cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

