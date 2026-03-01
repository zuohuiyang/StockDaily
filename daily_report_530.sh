#!/bin/bash
# 每日5:30投资组合报告生成脚本（收盘后数据）
cd /home/admin/.openclaw/workspace-wecom-group-wradsgkqaaewlr5s-tt0mr7r7n1d7ixq

# 使用优化后的报告生成器
python3 optimized_report_generator.py > daily_reports/$(date +%Y-%m-%d)_report.txt 2>&1

# 创建latest符号链接
ln -sf $(date +%Y-%m-%d)_report.txt daily_reports/latest_report.txt

echo "Daily report generated at $(date)"