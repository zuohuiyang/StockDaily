#!/bin/bash
# 每日投资组合报告生成脚本 - 修正版
cd /home/admin/.openclaw/workspace-wecom-group-wradsgkqaaewlr5s-tt0mr7r7n1d7ixq
python3 generate_standard_report_corrected.py > daily_reports/$(date +%Y-%m-%d)_report.txt 2>&1
cp daily_reports/$(date +%Y-%m-%d)_report.txt daily_reports/latest_report.txt