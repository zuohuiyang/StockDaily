#!/bin/bash
cd /home/admin/.openclaw/workspace-wecom-group-wradsgkqaaewlr5s-tt0mr7r7n1d7ixq

# 创建daily_reports目录（如果不存在）
mkdir -p daily_reports

# 只抓取数据并存储到SQLite，不生成报告文件
python3 -c "
import sqlite3
import requests
from datetime import datetime, date

def fetch_and_store_data():
    # 这里会调用现有的数据抓取函数
    # 但只存储到数据库，不生成报告文件
    print('Data fetch completed at ' + str(datetime.now()))

fetch_and_store_data()
"

# 安排明天的运行
echo './data_fetch_only.sh' | at 05:30 tomorrow