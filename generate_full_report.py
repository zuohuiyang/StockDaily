#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成完整投资组合报告（12只股票）
"""

import sqlite3
from datetime import datetime

def get_current_portfolio():
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    
    # 获取最新汇率
    cursor.execute('SELECT rate FROM exchange_rates WHERE from_currency = "USD" AND to_currency = "CNY" ORDER BY date DESC LIMIT 1')
    exchange_rate = cursor.fetchone()[0]
    
    # 获取所有持仓和最新价格
    cursor.execute('''
        SELECT h.code, h.name, h.quantity, h.currency, h.platform, sp.price
        FROM holdings h
        JOIN stock_prices sp ON h.code = sp.code
        WHERE sp.date = (SELECT MAX(date) FROM stock_prices)
        ORDER BY h.currency DESC, h.code
    ''')
    holdings = cursor.fetchall()
    
    conn.close()
    return holdings, exchange_rate

def generate_report():
    holdings, exchange_rate = get_current_portfolio()
    
    total_value = 0
    report_lines = []
    
    # 标题
    report_lines.append("=" * 120)
    report_lines.append("📈 股票投资组合完整报告")
    report_lines.append("=" * 120)
    report_lines.append("📊 报告时间: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    report_lines.append("-" * 120)
    
    # 持仓详情
    report_lines.append("📋 详细持仓:")
    report_lines.append("{:<12} {:<20} {:<8} {:<10} {:<12} {:<8} {:<15}".format(
        "股票代码", "股票名称", "数量", "价格", "价值(CNY)", "币种", "平台"))
    report_lines.append("-" * 120)
    
    for code, name, quantity, currency, platform, price in holdings:
        if currency == 'CNY':
            value_cny = price * quantity
        else:  # USD
            value_cny = price * quantity * exchange_rate
        
        total_value += value_cny
        
        report_lines.append("{:<12} {:<20} {:<8.1f} {:<10.3f} {:<12.2f} {:<8} {:<15}".format(
            code, name, quantity, price, value_cny, currency, platform))
    
    report_lines.append("-" * 120)
    report_lines.append("💰 总资产: {:.2f} CNY".format(total_value))
    report_lines.append("💱 汇率: 1 USD = {:.4f} CNY".format(exchange_rate))
    report_lines.append("=" * 120)
    
    return "\n".join(report_lines)

if __name__ == "__main__":
    report = generate_report()
    print(report)
    
    # 保存到文件
    with open('daily_reports/latest_full_report.txt', 'w') as f:
        f.write(report)