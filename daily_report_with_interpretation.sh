#!/bin/bash
# 每日05:30执行 - 抓取数据 + 生成解读 + 存储到数据库

cd /home/admin/.openclaw/workspace-wecom-group-wradsgkqaaewlr5s-tt0mr7r7n1d7ixq

# 1. 抓取最新的股票价格和汇率数据
python3 fetch_latest_data.py

# 2. 生成报告解读并存储到数据库
python3 generate_and_store_interpretation.py

echo "Daily data fetched and interpretation stored at $(date)"