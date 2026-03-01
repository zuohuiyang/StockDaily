from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from stock.db.connect import connect
from stock.db.schema import ensure_schema
from stock.ingestion.public.symbols import infer_market_currency


REQUIRED_COLUMNS = {"trade_time", "code", "side", "quantity", "price", "currency"}


def _normalize_header(name: str) -> str:
    return name.strip().lower()


def _import_id(source_file: str, payload: dict[str, str]) -> str:
    key = "|".join(
        [
            source_file,
            payload.get("trade_time", ""),
            payload.get("code", ""),
            payload.get("side", ""),
            payload.get("quantity", ""),
            payload.get("price", ""),
            payload.get("currency", ""),
            payload.get("fee", ""),
            payload.get("fx_rate", ""),
            payload.get("broker", ""),
            payload.get("note", ""),
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def import_transactions_csv(db_path: str, csv_path: str) -> int:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(str(path))

    inserted = 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV 缺少表头")
        field_map = {_normalize_header(n): n for n in reader.fieldnames}
        missing = [c for c in REQUIRED_COLUMNS if c not in field_map]
        if missing:
            raise ValueError(f"CSV 缺少必要字段: {', '.join(missing)}")

        with connect(db_path) as conn:
            ensure_schema(conn)

            for row in reader:
                payload = {_normalize_header(k): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
                code = payload["code"]
                currency = payload.get("currency") or infer_market_currency(code)[1]
                name = payload.get("name")
                market = payload.get("market")
                if not market:
                    market = infer_market_currency(code)[0]

                conn.execute(
                    """
                    INSERT INTO symbols(code, market, currency, name, active)
                    VALUES(?, ?, ?, ?, 1)
                    ON CONFLICT(code) DO UPDATE SET
                        market=COALESCE(excluded.market, symbols.market),
                        currency=COALESCE(excluded.currency, symbols.currency),
                        name=COALESCE(excluded.name, symbols.name),
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (code, market, currency, name),
                )

                iid = _import_id(str(path.name), payload)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO transactions(
                        trade_time, code, side, quantity, price, currency, fee, fx_rate, broker, note, import_id
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload["trade_time"],
                        code,
                        payload["side"].upper(),
                        float(payload["quantity"]),
                        float(payload["price"]),
                        currency,
                        float(payload.get("fee") or 0),
                        float(payload["fx_rate"]) if payload.get("fx_rate") else None,
                        payload.get("broker"),
                        payload.get("note"),
                        iid,
                    ),
                )
                changed = conn.execute("SELECT changes()").fetchone()[0]
                inserted += int(changed or 0)

            conn.commit()

    print(f"导入完成: {inserted} 条交易写入 {db_path}")
    return inserted
