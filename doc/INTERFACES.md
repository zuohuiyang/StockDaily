# 接口与调用约定

本文件定义“StockDaily 产线”的输入输出契约与对接方式，面向调用方（如 OpenClaw）与联调/运维场景。

## 运行与边界

- 开发环境：可在 Windows 运行
- 生产环境：运行在 Linux，并由 OpenClaw 通过子进程方式调用
- 对接方式：OpenClaw 负责触发运行；StockDaily 负责稳定落盘日报文件；OpenClaw 通过扫描归档文件获取结果并消费

## 输入（参数契约）

调用方通过命令行参数向 StockDaily 提供输入。输入分为三类：持仓参数（调用方提供）、公网行情采集范围、输出路径与报告日期等运行参数。

### 运行目录与初始化

- 工作目录：建议以项目目录作为工作目录运行
- 数据库文件：约定使用工作目录下的 `portfolio.db`
- 初始化：首次运行会自动创建所需数据表（若 `portfolio.db` 不存在则创建）

### 行情采集：指定某一天（推荐给 OpenClaw）

`python -m stock.ingest public-backfill`

- `--start YYYY-MM-DD`：开始日期
- `--end YYYY-MM-DD`：结束日期
- `--symbols`：需要采集的标的列表

OpenClaw 典型用法：
- 传入“昨天”作为 `start=end`，使采集范围与报告日期一致

### 行情采集：最近 N 天回补（便捷命令）

`python -m stock.ingest public-daily`

- `--lookback-days`：回补最近 N 天数据（默认 `7`）
- `--symbols`：需要采集的标的列表

### 日报生成：`python -m stock.report daily`

- `--date`：可选，生成指定日期报告；不传则使用数据库中“可用的最新 EOD 日期”
- `--out-dir`：输出目录（默认 `daily_reports`）
- `--latest-name`：可选，额外生成一个“latest 文件”（默认 `latest_report.md`）；OpenClaw 生产对接不依赖该文件

### 持仓参数传入

- `--position`：可重复传入，表示一个持仓；格式：`<asset_id>:<quantity>`
  - `asset_id`：A 股 6 位代码 / 美股 ticker / 虚拟币 BTC、ETH
  - `quantity`：数量（可为小数，适配虚拟币）

## 场景化调用流程

本章节按典型使用场景描述 OpenClaw 在生产环境（Linux）如何传参、如何初始化与如何日常调用。

### 场景 1：用户输入持仓（股票代码与数量）如何传入

约定：
- OpenClaw 调用“日报生成”时，使用一个或多个 `--position` 参数传入持仓集合
- 若持仓集合发生变化，OpenClaw 以当天调用时传入的 `--position` 为准

示例：

```bash
python -m stock.report daily \
  --date 2026-03-03 \
  --out-dir daily_reports \
  --position 600519:10 \
  --position AAPL:5
```

说明：
- `--position` 仅定义“持仓代码与数量”，不承载成本与交易流水
- 行情采集阶段需要知道要采集哪些标的；OpenClaw 应使用同一批标的作为 `--symbols` 传给行情采集命令（见场景 2/3）

### 场景 2：首次初始化某批股票代码的历史数据

目标：在首次接入一批标的时，先回补一段历史 EOD 价格与 USD/CNY 汇率，避免报告缺失。

调用方式：使用 `public-backfill` 指定起止日期，并显式传 `--symbols`。

示例（回补到昨天）：

```bash
python -m stock.ingest public-backfill \
  --start 2026-01-01 \
  --end 2026-03-03 \
  --symbols 600519 AAPL
```

### 场景 3：每天触发拉取“昨天”的股票与汇率数据

目标：每天只拉取“昨天”对应的 EOD 行情与 USD/CNY，使采集日期与日报日期一致。

调用方式：使用 `public-backfill` 且 `start=end=昨天`，并显式传 `--symbols`。

示例：

```bash
python -m stock.ingest public-backfill \
  --start 2026-03-03 \
  --end 2026-03-03 \
  --symbols 600519 AAPL
```

### 场景 4：每天触发生成“昨天”的日报

目标：在行情与汇率入库后，生成“昨天”的归档日报文件供 OpenClaw 扫描消费。

调用方式：调用 `stock.report daily` 并显式指定 `--date`。

示例：

```bash
python -m stock.report daily \
  --date 2026-03-03 \
  --out-dir daily_reports \
  --position 600519:10 \
  --position AAPL:5
```

成功判定（建议）：
- 子进程退出码为 `0`
- 且输出目录存在 `daily_reports/2026-03-03_report.md`

## 输出契约

### O1：Markdown 日报文件（固定路径）

- 归档：`daily_reports/YYYY-MM-DD_report.md`
- 编码：UTF-8
- 缺失展示：缺失即缺失，展示为 `-`；汇总不纳入缺失项，避免误导
- 行顺序：按 `asset_class`（CN_STOCK → US_STOCK → CRYPTO）再按 `asset_id` 升序

写入建议：
- 使用“先写临时文件再原子替换”的方式落盘，避免 OpenClaw 扫描时读到半截文件

### O2：进程退出码与可观测输出

- 退出码：
  - `0`：成功生成日报
  - 非 `0`：关键错误（例如无法确定报告日期、数据库不可用、输入账本不合法）
- 标准输出：成功时输出本次生成的归档报告路径（便于 OpenClaw 或外部调度消费）

## OpenClaw 对接

### OpenClaw 如何调用

- 由 OpenClaw 在 Linux 上通过子进程调用 StockDaily 的命令行入口
- 调用完成后以退出码判断成功/失败；成功后通过“按日期归档扫描”获取最新报告文件并消费

### OpenClaw 如何获取结果（按日期归档扫描）

- 扫描目录：`daily_reports/`
- 匹配模式：`*_report.md`
- 选择规则：按文件名日期或修改时间选择最新一份

## 典型运行方式（供调度/联调）

现有命令行入口：
- 公网采集入库（指定日期）：`python -m stock.ingest public-backfill --start YYYY-MM-DD --end YYYY-MM-DD`
- 公网采集入库（最近 N 天）：`python -m stock.ingest public-daily`
- 日报生成落盘：`python -m stock.report daily --out-dir daily_reports`

开发环境快捷入口（Windows）：
- `scripts/run_daily.ps1`
