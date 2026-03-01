# StockDaily

A 股 + 美股的本地“收盘价（EOD）投资组合日报”生成器：你维护交易/成本（可选），每天抓取行情与汇率，生成一份 Markdown 日报落盘，便于 OpenClaw 读取并转发结果。

## 你能得到什么

- 自动生成 `daily_reports/latest_report.md`（最新）与 `daily_reports/YYYY-MM-DD_report.md`（归档）
- 支持 A 股（6 位代码）与美股（如 NVDA/QQQ）
- 成本与盈亏（可选）：导入逐笔交易 CSV 后，按 FIFO 计算成本均价、已实现/未实现盈亏
- 缺失数据可见：缺少收盘价或汇率会在报告里标记，并避免纳入汇总

## 快速开始（推荐）

在仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_daily.ps1
```

执行完成后：

- 查看最新日报：`daily_reports/latest_report.md`
- 查看归档日报：`daily_reports/YYYY-MM-DD_report.md`

## 输入数据（两种方式）

### 方式 A：导入逐笔交易 CSV（推荐）

导入后会写入 `portfolio.db` 的 `transactions` 表，并自动 upsert 到 `symbols` 表。

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m stock.ingest --db portfolio.db private-import --file .\transactions.csv
```

CSV 必填字段（表头不区分大小写）：

- trade_time（ISO 时间或可解析时间字符串）
- code（A 股 6 位代码或美股 ticker）
- side（BUY/SELL）
- quantity
- price
- currency（CNY/USD）

可选字段：

- fee（手续费）
- fx_rate（成交时汇率，可为空）
- broker、note、name、market

最小示例：

```csv
trade_time,code,side,quantity,price,currency,fee
2026-02-01T10:00:00,600036,BUY,100,38.50,CNY,0
2026-02-02T10:00:00,NVDA,BUY,1,175.00,USD,0
```

### 方式 B：仅维护 holdings（无成本/盈亏）

如果你只想做“持仓估值”，且不关心成本与盈亏，可以维持旧的 `holdings` 表作为降级输入来源。此时报告里的“成本均价/盈亏”会显示为 `-`。

## 日常运行（不走脚本也可以）

仅采集公网数据（写入 prices_eod / fx_rates）：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m stock.ingest --db portfolio.db public-daily
```

生成日报（落盘到 daily_reports）：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m stock.report --db portfolio.db daily --out-dir daily_reports --latest-name latest_report.md
```

回补历史价格（用于补齐某段日期的收盘价）：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m stock.ingest --db portfolio.db public-backfill --start 2026-01-01 --end 2026-03-01
```

从旧库迁移（把 holdings/stock_prices/exchange_rates 合并到新结构）：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m stock.ingest --db portfolio.db migrate-db --sources portfolio.db stock_tracker.db stock_portfolio.db
```

## 输出说明

- `daily_reports/YYYY-MM-DD_report.md`：按估值日期归档
- `daily_reports/latest_report.md`：最新一份日报，供 OpenClaw 稳定读取

## 数据源

- A 股收盘价：腾讯日 K 线接口（qfq）
- 美股收盘价：Yahoo Finance chart 接口
- 汇率：写入 `fx_rates`（至少 USD/CNY；缺失会在报告里显示为“缺失”）

## 常见问题

### 报告提示“未找到 prices_eod 的可用日期”

先执行一次公网采集或数据库迁移：

- `powershell -ExecutionPolicy Bypass -File .\scripts\run_daily.ps1`
- `python -m stock.ingest --db portfolio.db public-daily`

### 报告里 USD/CNY 显示“缺失”

USD 仓位会无法换算为 CNY，总资产汇总会不计入对应仓位；你可以先补齐 `fx_rates` 再生成报告。

## 相关文档

- doc/ARCHITECTURE.md：分层与职责边界
- doc/PROJECT_ANALYSIS.md：入口、数据流、输入输出
- doc/PUBLIC_DATA_INGESTION.md：公网数据采集层方案
- doc/TRANSACTIONS_CSV.md：逐笔交易导入格式
