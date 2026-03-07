---
name: "stockdaily-openclaw"
description: "为 OpenClaw 生成投资组合日报并排障。用户提到股票/持仓/日报生成、历史回补或日报失败时触发。"
---

# StockDaily（OpenClaw Skill）

本技能用于在 OpenClaw 中统一编排 StockDaily 的“采集 → 生成日报 → 验收”流程。

## 触发条件

- 用户明确提到“股票”，并希望生成当日或指定日期的投资组合日报
- 用户提到“持仓”“A股”“美股”“BTC/ETH”，并要求产出日报文件
- 用户提到“回补历史行情”“初始化数据”后再生成日报
- 用户提到“日报生成失败/出错”，需要按标准流程排障

## 不触发条件

- 只做纯解释，不需要实际执行采集或生成日报
- 任务与股票日报无关

## 能力边界

- 支持 A 股 6 位代码、美股 ticker、加密货币 `BTC/ETH`
- 输出为 Markdown 日报文件，不负责交易系统下单

## 输入参数（request.json）

- `date`：`YYYY-MM-DD`
- `positions`：`<asset_id>:<quantity>` 数组
- `db_path`（可选）：默认 `portfolio.db`
- `out_dir`（可选）：默认 `daily_reports`
- `backfill`（可选）：`{ "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" }`

## 执行步骤

1) 解析并校验输入参数  
2) 推导 `--symbols`，先执行 `stock.ingest public-backfill`  
3) 执行 `stock.report daily` 生成归档日报  
4) 验证报告文件存在并返回路径

## 成功判定

- 退出码为 `0`
- 存在 `daily_reports/YYYY-MM-DD_report.md`
- 标准输出为归档日报路径

## 失败处理

- 参数错误：返回非 0，提示缺失/格式不合法字段
- 数据缺失：可先执行回补区间，再重新生成
- 环境错误：检查工作目录、`PYTHONPATH`、数据库路径、Python 版本

## 使用方式（OpenClaw clone 即用）

```bash
./run.sh --request examples/request.example.json
```

## 参考

- 请求示例：[request.example.json](examples/request.example.json)
- 机读清单：[skill.yaml](skill.yaml)
- 对接契约：[INTERFACES.md](doc/INTERFACES.md)
- 故障排查：[TROUBLESHOOTING.md](doc/TROUBLESHOOTING.md)
