#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按需生成投资组合报告
从SQLite数据库读取最新数据，实时生成标准化报告
"""

import sqlite3
from datetime import datetime, date, timedelta

def get_latest_portfolio_data():
    """从数据库获取最新的投资组合数据"""
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    
    # 获取最新日期
    cursor.execute('SELECT MAX(date) FROM stock_prices')
    latest_date = cursor.fetchone()[0]
    
    if not latest_date:
        print("数据库中没有价格数据")
        return None
    
    # 获取汇率（使用最新汇率）
    cursor.execute('SELECT rate FROM exchange_rates WHERE from_currency = "USD" AND to_currency = "CNY" ORDER BY date DESC LIMIT 1')
    exchange_rate_result = cursor.fetchone()
    exchange_rate = exchange_rate_result[0] if exchange_rate_result else 6.8803
    
    # 获取所有持仓
    cursor.execute('SELECT code, name, quantity, currency, platform FROM holdings')
    holdings = cursor.fetchall()
    
    # 获取今日价格
    today_holdings = []
    today_total = 0
    
    for code, name, quantity, currency, platform in holdings:
        if currency == 'CNY':
            cursor.execute('SELECT price FROM stock_prices WHERE code = ? AND date = ?', (code, latest_date))
            result = cursor.fetchone()
            price = result[0] if result else 0
            value_cny = price * quantity
        else:  # USD
            cursor.execute('SELECT price FROM stock_prices WHERE code = ? AND date = ?', (code, latest_date))
            result = cursor.fetchone()
            price = result[0] if result else 0
            value_usd = price * quantity
            value_cny = value_usd * exchange_rate
        
        today_holdings.append({
            'code': code,
            'name': name,
            'quantity': quantity,
            'price': price,
            'value_cny': value_cny,
            'currency': currency,
            'platform': platform
        })
        today_total += value_cny
    
    # 获取昨日和年初数据用于对比
    yesterday = (datetime.strptime(latest_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    year_start = '2026-01-02'
    
    # 计算昨日总资产
    yesterday_total = 0
    for code, name, quantity, currency, platform in holdings:
        if currency == 'CNY':
            cursor.execute('SELECT price FROM stock_prices WHERE code = ? AND date = ?', (code, yesterday))
            result = cursor.fetchone()
            price = result[0] if result else 0
            value_cny = price * quantity
        else:
            cursor.execute('SELECT price FROM stock_prices WHERE code = ? AND date = ?', (code, yesterday))
            result = cursor.fetchone()
            price = result[0] if result else 0
            value_usd = price * quantity
            value_cny = value_usd * exchange_rate
        yesterday_total += value_cny
    
    # 计算年初总资产  
    year_start_total = 0
    for code, name, quantity, currency, platform in holdings:
        if currency == 'CNY':
            cursor.execute('SELECT price FROM stock_prices WHERE code = ? AND date = ?', (code, year_start))
            result = cursor.fetchone()
            price = result[0] if result else 0
            value_cny = price * quantity
        else:
            cursor.execute('SELECT price FROM stock_prices WHERE code = ? AND date = ?', (code, year_start))
            result = cursor.fetchone()
            price = result[0] if result else 0
            value_usd = price * quantity
            value_cny = value_usd * exchange_rate
        year_start_total += value_cny
    
    conn.close()
    
    return {
        'date': latest_date,
        'holdings': today_holdings,
        'total': today_total,
        'yesterday_total': yesterday_total,
        'year_start_total': year_start_total,
        'exchange_rate': exchange_rate
    }

def generate_standard_report(data):
    """生成标准化报告"""
    report_lines = []
    report_lines.append("=" * 120)
    report_lines.append("📈 股票投资组合标准化报告")
    report_lines.append("=" * 120)
    report_lines.append("📊 报告时间: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    report_lines.append("-" * 120)
    
    # 今日详细持仓
    report_lines.append("📋 今日详细持仓:")
    report_lines.append("{:<12} {:<20} {:<8} {:<10} {:<12} {:<8} {:<15}".format(
        "股票代码", "股票名称", "数量", "价格", "价值(CNY)", "币种", "平台"))
    report_lines.append("-" * 120)
    
    for holding in data['holdings']:
        report_lines.append("{:<12} {:<20} {:<8.1f} {:<10.3f} {:<12.2f} {:<8} {:<15}".format(
            holding['code'], holding['name'], holding['quantity'], 
            holding['price'], holding['value_cny'], holding['currency'], holding['platform']))
    
    report_lines.append("-" * 120)
    report_lines.append("💰 今日总资产: {:.2f} CNY".format(data['total']))
    report_lines.append("")
    
    # 完整对比分析
    report_lines.append("🔄 完整对比分析:")
    report_lines.append("   年初资产 (2026-01-02): {:.2f} CNY".format(data['year_start_total']))
    report_lines.append("   昨日资产 ({}): {:.2f} CNY".format(
        (datetime.strptime(data['date'], '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d'),
        data['yesterday_total']))
    report_lines.append("   今日资产 ({}): {:.2f} CNY".format(data['date'], data['total']))
    report_lines.append("")
    
    # 变化详情
    change_vs_yesterday = data['total'] - data['yesterday_total']
    change_pct_vs_yesterday = (change_vs_yesterday / data['yesterday_total']) * 100 if data['yesterday_total'] > 0 else 0
    
    change_vs_year_start = data['total'] - data['year_start_total']
    change_pct_vs_year_start = (change_vs_year_start / data['year_start_total']) * 100 if data['year_start_total'] > 0 else 0
    
    report_lines.append("📊 变化详情:")
    report_lines.append("   相比昨日: {:+.2f} CNY ({:+.2f}%)".format(change_vs_yesterday, change_pct_vs_yesterday))
    report_lines.append("     (昨日: {:.2f} CNY → 今日: {:.2f} CNY)".format(data['yesterday_total'], data['total']))
    report_lines.append("   相比年初: {:+.2f} CNY ({:+.2f}%)".format(change_vs_year_start, change_pct_vs_year_start))
    report_lines.append("     (年初: {:.2f} CNY → 今日: {:.2f} CNY)".format(data['year_start_total'], data['total']))
    report_lines.append("")
    
    # 波动解读
    report_lines.append("🎯 波动解读:")
    if abs(change_pct_vs_yesterday) > 1.0:
        if change_vs_yesterday > 0:
            report_lines.append("   今日投资组合表现强劲，主要受益于市场整体上涨。")
        else:
            report_lines.append("   今日投资组合出现回调，主要受市场短期调整影响。")
    else:
        report_lines.append("   今日投资组合波动较小，保持相对稳定。")
    
    report_lines.append("=" * 120)
    
    return "\n".join(report_lines)

def main():
    data = get_latest_portfolio_data()
    if data:
        report = generate_standard_report(data)
        print(report)
    else:
        print("无法生成报告：数据库中缺少必要的数据")

if __name__ == "__main__":
    main()