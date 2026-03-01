# 项目分析：股票投资组合分析与每日报告系统

## 1. 项目做什么（功能与边界）

这个仓库是一个以 SQLite 为核心的数据驱动“投资组合日报”系统：以持仓为输入，抓取行情/汇率（或使用数据库中已有记录），把价格写入数据库，按日期做估值与对比（今日 vs 昨日/年初等），最终输出一份文本或 Markdown 报告。

从代码现状看，它同时包含多条实现线：
- **主线（推荐）**：`portfolio.db` + 报告生成脚本（尤其是优化版）输出日报到 stdout，再由脚本重定向到 `daily_reports/`。
- **数据补全/修复线**：当某日缺失价格时，通过抓历史/插值写回 `portfolio.db.stock_prices`。
- **多智能体实验线**：协调器从 DB 组装组合数据，把 JSON 通过 stdin 发送给多个 agent 并行处理，再输出汇总 JSON。
- **追踪器线（独立 DB）**：`stock_tracker*.py` 使用 `stock_tracker.db/stock_portfolio.db`（自建表）做交互式记录与估值。
- **OpenClaw/Qwen 适配**：`qwen-cli-adapter.py` 作为 CLI ↔ DashScope Qwen API 的桥接器，与日报主线基本独立。

## 2. 如何实现（模块、关键文件与数据流）

### 2.1 模块划分（按职责）

| 模块 | 责任 | 关键文件 |
|---|---|---|
| 存储（SQLite） | 存放持仓、每日价格、汇率等 | [README.md](file:///c:/project/stock/README.md#L54-L75) |
| 当日抓取 | 按持仓抓现价并写入 `stock_prices` | [stock_price_fetcher.py](file:///c:/project/stock/stock_price_fetcher.py#L11-L104) |
| 历史补全 | 为指定日期补齐缺失价格 | [fetch_historical_data.py](file:///c:/project/stock/fetch_historical_data.py#L61-L112) |
| 缺失修复（插值） | 用相邻两天均值插入缺失日价格 | [repair_missing_data.py](file:///c:/project/stock/repair_missing_data.py#L17-L67) |
| 日报生成（主线） | 从 DB 读取最新日期与价格，计算估值与对比，输出报告 | [optimized_report_generator.py](file:///c:/project/stock/optimized_report_generator.py#L13-L255) |
| 报告变体 | 标准/最终/按需/完整报告等脚本 | [generate_standard_report_final.py](file:///c:/project/stock/generate_standard_report_final.py#L11-L148)、[generate_report_on_demand.py](file:///c:/project/stock/generate_report_on_demand.py#L11-L178)、[generate_full_report.py](file:///c:/project/stock/generate_full_report.py#L10-L74) |
| 多智能体（实验） | 并行执行 3 个 agent，stdin/stdout JSON 协作 | [multi_agent_coordinator.py](file:///c:/project/stock/multi_agent_coordinator.py#L14-L173) |
| 调度/脚本封装 | 定时执行并落地报告文件 | [daily_report_530.sh](file:///c:/project/stock/daily_report_530.sh#L1-L11)、[smart_daily_report.sh](file:///c:/project/stock/smart_daily_report.sh#L1-L15)、[local_cron_scheduler.py](file:///c:/project/stock/local_cron_scheduler.py#L14-L79) |
| 追踪器（独立实现线） | 读取 JSON 或自建 SQLite，交互式/简化估值并写报告 | [stock_tracker.py](file:///c:/project/stock/stock_tracker.py#L14-L170)、[stock_tracker_sqlite.py](file:///c:/project/stock/stock_tracker_sqlite.py#L15-L263) |
| OpenClaw/Qwen 适配 | 将 OpenClaw CLI 参数转为 Qwen API 请求并输出 JSON | [qwen-cli-adapter.py](file:///c:/project/stock/qwen-cli-adapter.py#L19-L125) |

### 2.2 主线数据流（portfolio.db → 日报）

典型链路（按现有脚本）：
1. **持仓来源**：`portfolio.db.holdings`  
   - 报告读取持仓：`SELECT code,name,quantity,currency,platform FROM holdings`  
   - 参考：[get_holdings](file:///c:/project/stock/optimized_report_generator.py#L59-L74)
2. **价格来源**：`portfolio.db.stock_prices`  
   - 报告取“最新日期”：`SELECT DISTINCT date FROM stock_prices ORDER BY date DESC`  
   - 参考：[get_all_dates](file:///c:/project/stock/optimized_report_generator.py#L43-L58)、[get_today_date](file:///c:/project/stock/optimized_report_generator.py#L141-L145)
3. **估值与对比**：
   - 今日、昨日、年初三段估值（年初日期在代码里写死为 `2026-01-02`）  
   - 参考：[generate_report](file:///c:/project/stock/optimized_report_generator.py#L159-L193)
4. **输出**：
   - `optimized_report_generator.py` 直接 `print(formatted_report)` 到 stdout  
   - 参考：[main](file:///c:/project/stock/optimized_report_generator.py#L245-L255)
5. **落盘（脚本封装）**：
   - `daily_report_530.sh` 把 stdout 重定向到 `daily_reports/YYYY-MM-DD_report.txt` 并维护 `latest_report.txt`  
   - 参考：[daily_report_530.sh](file:///c:/project/stock/daily_report_530.sh#L5-L10)

## 3. 核心数据模型（按脚本实际使用）

### 3.1 README 约定的 3 张核心表

| 表 | 字段（README 约定） | 用途 |
|---|---|---|
| `holdings` | `code,name,quantity,currency,platform` | 持仓清单 |
| `stock_prices` | `code,price,currency,date,source` | 每日价格（可多来源） |
| `exchange_rates` | `from_currency,to_currency,rate,date` | 每日汇率 |

参考：[README.md](file:///c:/project/stock/README.md#L54-L75)

### 3.2 代码对表结构的“隐含要求”

不同脚本对表字段存在差异化假设：
- 多数脚本只依赖 `stock_prices(code,price,currency,date,source)`，缺失价格时直接用 `0`（例如 [optimized_report_generator.py](file:///c:/project/stock/optimized_report_generator.py#L75-L97)、[generate_report_on_demand.py](file:///c:/project/stock/generate_report_on_demand.py#L11-L106)）。
- `detailed_analysis_report.py` 查询 `stock_prices` 时使用了 `created_at` 字段（`ORDER BY created_at DESC`），这意味着实际 `portfolio.db.stock_prices` 可能包含 `created_at`，或该脚本与当前 DB 结构不完全一致。参考：[detailed_analysis_report.py](file:///c:/project/stock/detailed_analysis_report.py#L21-L27)。

如果你希望 DB 结构“以代码为准”统一化，可以先以 SQLite 追踪器的建表语句作为参考（但它默认用 `stock_tracker.db`）：  
参考：[stock_tracker_sqlite.py](file:///c:/project/stock/stock_tracker_sqlite.py#L20-L76)

## 4. 输入与输出分别是什么（入口清单）

下面按“你直接运行一个脚本/脚本组合”来列输入与输出。

| 入口 | 用途 | 输入 | 输出 |
|---|---|---|---|
| `python optimized_report_generator.py` | 生成 Markdown 日报（主线） | `portfolio.db`：`holdings`、`stock_prices`、`exchange_rates` | stdout：Markdown 报告 |
| `./daily_report_530.sh` | 定时生成日报并维护 latest | 依赖上条脚本；脚本内 hardcode `cd` 路径 | `daily_reports/YYYY-MM-DD_report.txt`、`daily_reports/latest_report.txt`（符号链接） |
| `python stock_price_fetcher.py` | 更新当日价格写入 DB | `portfolio.db.holdings`；`api_config.json`（Alpha Vantage key，可选）；网络接口 | 写入 `portfolio.db.stock_prices`；stdout 打印每只股票结果 |
| `python fetch_historical_data.py` | 修复指定日期缺失历史价格 | `portfolio.db.holdings`；网络接口（A 股腾讯历史 / 美股 Yahoo） | 写入 `portfolio.db.stock_prices`（`source='historical_fix'`）；stdout 日志 |
| `python repair_missing_data.py` | 对固定日期做插值补点 | `portfolio.db.holdings`；`portfolio.db.stock_prices` 相邻两天数据 | 写入 `portfolio.db.stock_prices`（`source='interpolated'`）；stdout 日志 |
| `python generate_report_on_demand.py` | 读取 DB 最新日期并输出“标准报告” | `portfolio.db`：同主线 | stdout：文本报告 |
| `python generate_full_report.py` | 生成“完整报告”并落盘 | `portfolio.db`（要求 `exchange_rates` 最新记录存在） | stdout；并写 `daily_reports/latest_full_report.txt` |
| `python detailed_analysis_report.py` | 两日对比与个股贡献分析 | `portfolio.db`；（可能依赖 `stock_prices.created_at`） | stdout：文本分析报告 |
| `python multi_agent_coordinator.py` | 并行跑 3 个 agent 并汇总 JSON | `portfolio.db`（最新日期与价格）；子进程 stdin/stdout JSON | stdout：JSON（含各 agent 结果） |
| `python stock_tracker.py` | 简化追踪器（不依赖 DB） | `portfolio.json`（可选，默认示例）；网络接口（新浪/汇率 API） | stdout：文本报告；并写 `latest_report.txt` |
| `python stock_tracker_sqlite.py` | 交互式追踪器（独立 DB） | `stock_tracker.db`（脚本自建表）；手工输入价格/汇率（必要时） | stdout：表格；写入 `stock_tracker.db` |
| `python local_cron_scheduler.py --run` | Python schedule 本地调度器 | `cron_config` 未用；脚本内配置 `daily_report_530.sh` | 运行日志；注意它会用 Python 去执行 `.sh`（存在不匹配风险） |
| `python qwen-cli-adapter.py ...` | OpenClaw ↔ Qwen API 桥接 | CLI 参数：`--model/-p/--append-system-prompt/...`；环境变量 `DASHSCOPE_API_KEY`（建议） | stdout：OpenClaw 期望的 JSON |

## 5. 多智能体 stdin/stdout JSON 协议（实验线）

### 5.1 Coordinator → Agent（stdin JSON）

协调器给每个 agent 的输入大致是：

```json
{
  "task": "analyze_portfolio | monitor_performance | generate_report",
  "portfolio_data": {
    "date": "YYYY-MM-DD",
    "holdings": [
      {
        "code": "SOXX",
        "name": "xxx",
        "quantity": 1,
        "price": 123.45,
        "currency": "USD",
        "platform": "xxx"
      }
    ]
  },
  "...": "不同 agent 的额外参数"
}
```

参考：[generate_comprehensive_report](file:///c:/project/stock/multi_agent_coordinator.py#L92-L127)

### 5.2 Agent → Coordinator（stdout JSON）

- `investment_analyst_agent.py` 输出结构带 `success/data`：参考 [investment_analyst_agent.py](file:///c:/project/stock/investment_analyst_agent.py#L11-L111)
- `performance_monitor_agent.py` 输出结构为 `{timestamp, metrics, status}`：参考 [performance_monitor_agent.py](file:///c:/project/stock/performance_monitor_agent.py#L12-L80)
- `report_generator_agent.py` 输出结构为 `{report_content, total_value, status}`：参考 [report_generator_agent.py](file:///c:/project/stock/report_generator_agent.py#L11-L111)

协调器会把 agent 的 stdout JSON 再包一层 `{'success': True, 'data': <agent_json>}` 并汇总输出：参考 [execute_agent](file:///c:/project/stock/multi_agent_coordinator.py#L23-L64)

## 6. 其他实现线与差异说明

### 6.1 追踪器线 vs 主线

- `stock_tracker.py`：以 `portfolio.json` 为输入（可缺省），直接走 HTTP 接口抓价和汇率，输出文本并写 `latest_report.txt`。参考：[stock_tracker.py](file:///c:/project/stock/stock_tracker.py#L14-L170)
- `stock_tracker_sqlite.py`：自建 `stock_tracker.db`，强调“手动补价格/汇率”，适合离线或小规模试验。参考：[stock_tracker_sqlite.py](file:///c:/project/stock/stock_tracker_sqlite.py#L20-L235)
- 主线 `portfolio.db`：更偏“事实记录（持仓/价格/汇率）→ 报告生成”，并且有多脚本写入同一张 `stock_prices`。

### 6.2 OpenClaw/Qwen 适配

`qwen-cli-adapter.py` 的输入是 OpenClaw CLI 风格参数（`-p` prompt、`--model` 等），输出是 OpenClaw 期望的 JSON（`text/session_id/usage`）。参考：[qwen-cli-adapter.py](file:///c:/project/stock/qwen-cli-adapter.py#L32-L119)

## 7. 已知不一致点与运行注意事项（基于现有代码）

1. **“不估算价格”准则与实现不一致**：多份报告脚本在缺失价格时直接用 `0`，会让总资产被动“估算为更低”。示例：`result else 0`（[optimized_report_generator.py](file:///c:/project/stock/optimized_report_generator.py#L88-L97)）。
2. **插值修复与准则冲突**：`repair_missing_data.py` 明确用相邻两天均值插入缺失日价格（[repair_missing_data.py](file:///c:/project/stock/repair_missing_data.py#L35-L58)），这属于“估算/插值”，与 README 的“缺失保持缺失”不一致。
3. **汇率兜底为固定值**：多个脚本在汇率缺失时回退到固定数字（例如 6.8803/6.85），会影响 USD 资产换算。示例：[get_exchange_rate](file:///c:/project/stock/optimized_report_generator.py#L26-L41)、[stock_price_fetcher.py](file:///c:/project/stock/stock_price_fetcher.py#L48-L61)。
4. **部分脚本日期写死**：例如 `generate_standard_report_final.py` 把 today/yesterday/year_start 写死为 2026-02-27/26/01-02（[generate_standard_report_final.py](file:///c:/project/stock/generate_standard_report_final.py#L16-L20)）。
5. **多智能体输入字段不完全匹配**：协调器传入的 holding 没有 `value_cny`，而投资分析 agent 的总资产计算用的是 `value_cny`，导致结果可能为 0。参考：[investment_analyst_agent.py](file:///c:/project/stock/investment_analyst_agent.py#L14-L25) 与 [multi_agent_coordinator.py](file:///c:/project/stock/multi_agent_coordinator.py#L145-L163)。
6. **潜在安全风险**：
   - `fetch_historical_data.py` 解析腾讯历史接口时使用 `eval`（[fetch_historical_data.py](file:///c:/project/stock/fetch_historical_data.py#L47-L57)），不建议在不可信输入下使用。
   - `qwen-cli-adapter.py` 包含硬编码的 API key（[qwen-cli-adapter.py](file:///c:/project/stock/qwen-cli-adapter.py#L21-L28)），仓库层面存在泄露风险。
7. **跨平台/调度不匹配**：
   - `.sh` 脚本内 hardcode 了 Linux 路径并使用 `at`，在 Windows 环境不可直接用（例如 [daily_report_530.sh](file:///c:/project/stock/daily_report_530.sh#L3-L10)）。
   - `local_cron_scheduler.py` 通过 `sys.executable` 执行 `daily_report_530.sh`（[local_cron_scheduler.py](file:///c:/project/stock/local_cron_scheduler.py#L35-L45)），脚本类型不匹配会导致失败。

## 8. 你关心的“输入/输出”一句话总结

- **输入**：核心是 `portfolio.db`（持仓、价格、汇率），加上少量 JSON 配置（`api_config.json`、追踪器的 `portfolio.json`）与外部行情/汇率网络接口。
- **输出**：核心是“报告文本/Markdown”（stdout 或落地到 `daily_reports/`、`latest_report.txt`），以及对 SQLite 的写入（更新/补全 `stock_prices`，部分实现线还会写 `exchange_rates/portfolio_values`）。

