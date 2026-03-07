#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"

request=""
dry_run="0"

while [ $# -gt 0 ]; do
  case "$1" in
    --request)
      request="${2:-}"
      shift 2
      ;;
    --dry-run)
      dry_run="1"
      shift 1
      ;;
    *)
      echo "未知参数: $1" >&2
      exit 2
      ;;
  esac
done

if [ -z "$request" ]; then
  echo "用法: ./run.sh --request <request.json> [--dry-run]" >&2
  exit 2
fi

if command -v python3 >/dev/null 2>&1; then
  py="python3"
elif command -v python >/dev/null 2>&1; then
  py="python"
else
  echo "未找到 python3/python" >&2
  exit 1
fi

"$py" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("需要 Python >= 3.10")
PY

if [ "${STOCKDAILY_NO_VENV:-0}" != "1" ]; then
  if [ ! -x ".venv/bin/python" ]; then
    "$py" -m venv .venv
  fi
  py=".venv/bin/python"
fi

export PYTHONPATH="$repo_root/src"

mapfile -t ingest_argv < <("$py" - "$request" <<'PY'
import json
import re
import sys
from pathlib import Path

req_path = Path(sys.argv[1])
with req_path.open("r", encoding="utf-8") as f:
    req = json.load(f)

date = str(req.get("date") or "").strip()
if not date:
    raise SystemExit("request.date 不能为空")

positions = req.get("positions")
if not isinstance(positions, list) or not positions:
    raise SystemExit("request.positions 必须为非空数组")

db_path = str(req.get("db_path") or "portfolio.db")
out_dir = str(req.get("out_dir") or "daily_reports")

backfill = req.get("backfill")
if backfill is None:
    start = date
    end = date
else:
    if not isinstance(backfill, dict):
        raise SystemExit("request.backfill 必须为对象")
    start = str(backfill.get("start") or "").strip()
    end = str(backfill.get("end") or "").strip()
    if not start or not end:
        raise SystemExit("request.backfill.start/end 不能为空")

symbols: list[str] = []
for i, p in enumerate(positions):
    if not isinstance(p, str) or ":" not in p:
        raise SystemExit(f"positions[{i}] 格式错误，应为 asset_id:quantity")
    asset_id = p.split(":", 1)[0].strip()
    if not asset_id:
        raise SystemExit(f"positions[{i}] asset_id 为空")
    up = asset_id.upper()
    if up in ("BTC", "ETH"):
        asset_id = up
    if not re.fullmatch(r"\d{6}", asset_id) and not re.fullmatch(r"[A-Za-z0-9.\-]+", asset_id):
        raise SystemExit(f"positions[{i}] asset_id 非法: {asset_id}")
    symbols.append(asset_id)

print("--db")
print(db_path)
print("public-backfill")
print("--start")
print(start)
print("--end")
print(end)
print("--symbols")
for s in symbols:
    print(s)
PY
)

mapfile -t report_argv < <("$py" - "$request" <<'PY'
import json
import sys
from pathlib import Path

req_path = Path(sys.argv[1])
with req_path.open("r", encoding="utf-8") as f:
    req = json.load(f)

date = str(req.get("date") or "").strip()
if not date:
    raise SystemExit("request.date 不能为空")

positions = req.get("positions")
if not isinstance(positions, list) or not positions:
    raise SystemExit("request.positions 必须为非空数组")

db_path = str(req.get("db_path") or "portfolio.db")
out_dir = str(req.get("out_dir") or "daily_reports")

print("--db")
print(db_path)
print("daily")
print("--date")
print(date)
print("--out-dir")
print(out_dir)
for p in positions:
    print("--position")
    print(str(p))
PY
)

if [ "$dry_run" = "1" ]; then
  printf '%s\n' "$py" "-m" "stock.ingest" "${ingest_argv[@]}"
  printf '%s\n' "$py" "-m" "stock.report" "${report_argv[@]}"
  exit 0
fi

"$py" -m stock.ingest "${ingest_argv[@]}"
report_path="$("$py" -m stock.report "${report_argv[@]}")"

if [ ! -f "$report_path" ]; then
  echo "未找到报告文件: $report_path" >&2
  exit 1
fi

echo "$report_path"
