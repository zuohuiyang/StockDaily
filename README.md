# StockDaily

A 股 + 美股的本地“收盘价（EOD）投资组合日报”生成器：由 OpenClaw 在 Linux 生产环境中调用，按固定目录落盘 Markdown 日报，供 OpenClaw 扫描归档文件并消费结果。

## 你能得到什么

- 自动生成 `daily_reports/YYYY-MM-DD_report.md`（按日期归档）
- 支持 A 股（6 位代码）与美股 ticker
- 每日采集：股票 EOD 收盘价 + USD/CNY 汇率
- 缺失不估算：缺少行情或汇率时不纳入汇总，并在报告中体现

## 文档

- 调用约定（给 OpenClaw/调用方）：[doc/INTERFACES.md](doc/INTERFACES.md)
- 分层架构（给开发者）：[doc/ARCHITECTURE.md](doc/ARCHITECTURE.md)

## 生产调用（OpenClaw）

生产环境中，OpenClaw 通过子进程方式调用本项目的命令行入口，并通过扫描 `daily_reports/*_report.md` 获取最新报告文件。

完整参数与场景化流程以 [doc/INTERFACES.md](doc/INTERFACES.md) 为准。最常见的“昨天”流程是：

1) 传入持仓（股票代码与数量）
- 在“生成日报”命令中，通过一个或多个 `--position <asset_id>:<quantity>` 传入

2) 初始化历史数据（首次接入某批标的）
- 运行 `public-backfill` 回补一段历史区间，并显式传入 `--symbols` 标的列表

3) 每天采集“昨天”的行情与汇率
- 运行 `public-backfill`，并将 `--start` 与 `--end` 都设置为昨天，同时显式传入 `--symbols`

4) 每天生成“昨天”的日报
- 运行 `stock.report daily --date <昨天>`，并传入同一批 `--position`

日报落盘后，OpenClaw 通过扫描获取：

- 输出目录：`daily_reports/`
- 文件模式：`*_report.md`
- 选择规则：按文件名日期或修改时间选择最新一份

## 开发者本地运行（可选）

本项目使用 `src/` 作为源码目录，建议通过设置 `PYTHONPATH` 运行模块入口。

Linux/macOS：

```bash
export PYTHONPATH="$(pwd)/src"
```

Windows PowerShell：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
```

命令行入口：

- 行情采集：`python -m stock.ingest public-backfill` / `python -m stock.ingest public-daily`
- 日报生成：`python -m stock.report daily`
