#!/bin/bash
# 智能每日报告生成器 - 自动安排下次运行

# 创建报告目录
mkdir -p daily_reports

# 生成报告
cd /home/admin/.openclaw/workspace-wecom-group-wradsgkqaaewlr5s-tt0mr7r7n1d7ixq
python3 generate_standard_report_final.py > "daily_reports/$(date +%Y-%m-%d)_report.txt"
cp "daily_reports/$(date +%Y-%m-%d)_report.txt" daily_reports/latest_report.txt

# 安排明天的运行（05:30）
echo "/home/admin/.openclaw/workspace-wecom-group-wradsgkqaaewlr5s-tt0mr7r7n1d7ixq/smart_daily_report.sh" | at 05:30 tomorrow

echo "Daily report generated and next run scheduled for tomorrow 05:30"