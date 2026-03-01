# 逐笔交易导入格式（transactions.csv）

该 CSV 用于导入你的私有账本数据到统一数据库的 `transactions` 表，支撑 FIFO 成本与盈亏计算。

## 必填字段

- `trade_time`：交易时间（建议 ISO 格式，例如 `2026-03-01T09:30:00`）
- `code`：标的代码（A 股 6 位数字；美股如 `AAPL`、`SOXX`）
- `side`：`BUY` 或 `SELL`
- `quantity`：数量（正数）
- `price`：成交价（按标的计价币种）
- `currency`：`CNY` 或 `USD`

## 可选字段

- `fee`：手续费（同 `currency`）
- `fx_rate`：交易当日 USD/CNY 汇率（可留空；留空则由计算层按规则补齐）
- `broker`：券商/平台（字符串）
- `note`：备注（字符串）
- `name`：标的名称（用于填充 `symbols` 表，可选）
- `market`：市场标记（`CN`/`US`，可选；不填则按 `code` 推断）

## 示例

参见：[transactions.example.csv](file:///c:/project/stock/doc/transactions.example.csv)

## 导入命令（Windows）

```powershell
$env:PYTHONPATH='src'
python -m stock.ingest --db portfolio.db private-import --file doc/transactions.example.csv
```

