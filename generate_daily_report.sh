#!/bin/bash
# 每日投资组合报告生成脚本
cd /home/admin/.openclaw/workspace-wecom-group-wradsgkqaaewlr5s-tt0mr7r7n1d7ixq
python3 generate_standard_report_final.py > daily_reports/report_$(date +%Y-%m-%d).txt 2>&1