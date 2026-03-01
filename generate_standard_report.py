#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标准化投资组合报告生成器
按照统一模板生成每日报告
"""

import sqlite3
from datetime import datetime, date
import sys

def get_latest_data():
    """获取最新的持仓和价格数据"""
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    
    # 获取今日日期
    today = '2026-02-27'
    yesterday = '2026-02-26' 
    year_start = '2026-01-02'
    
    # 获取汇率（使用最新汇率）
    cursor.execute('SELECT rate FROM exchange_rates WHERE from_currency = "USD" AND to_currency = "CNY" ORDER BY date DESC LIMIT 1')
    exchange_rate = cursor.fetchone()[0] if cursor.fetchone() else 6.8803
    
    # 获取所有持仓
    cursor.execute('SELECT code, name, quantity, currency, platform FROM holdings')
    holdings = cursor.fetchall()
    
    # 获取各时间点的价格
    portfolio_data = {}
    for day_label, day_date in [('today', today), ('yesterday', yesterday), ('year_start', year_start)]:
        day_total = 0
        day_holdings = []
        
        for code, name, quantity, currency, platform in holdings:
            if currency == 'CNY':
                # 获取人民币股票价格
                cursor.execute('SELECT price FROM stock_prices WHERE code = ? AND date = ?', (code, day_date))
                result = cursor.fetchone()
                price = result[0] if result else 0
                value_cny = price * quantity
            else:  # USD
                # 获取美元股票价格
                cursor.execute('SELECT price FROM stock_prices WHERE code = ? AND date = ?', (code, day_date))
                result = cursor.fetchone()
                price = result[0] if result else 0
                value_usd = price * quantity
                value_cny = value_usd * exchange_rate
            
            day_holdings.append({
                'code': code,
                'name': name,
                'quantity': quantity,
                'price': price,
                'value_cny': value_cny,
                'currency': currency,
                'platform': platform
            })
            day_total += value_cny
        
        portfolio_data[day_label] = {
            'date': day_date,
            'total': day_total,
            'holdings': day_holdings
        }
    
    conn.close()
    return portfolio_data, exchange_rate

def format_report(portfolio_data, exchange_rate):
    """按照标准模板格式化报告"""
    today_data = portfolio_data['today']
    yesterday_data = portfolio_data['yesterday'] 
    year_start_data = portfolio_data['year_start']
    
    # 计算变化
    today_total = today_data['total']
    yesterday_total = yesterday_data['total']
    year_start_total = year_start_data['total']
    
    change_vs_yesterday = today_total - yesterday_total
    change_pct_vs_yesterday = (change_vs_yesterday / yesterday_total) * 100 if yesterday_total > 0 else 0
    
    change_vs_year_start = today_total - year_start_total
    change_pct_vs_year_start = (change_vs_year_start / year_start_total) * 100 if year_start_total > 0 else 0
    
    # 生成报告
    report = []
    report.append("=" * 120)
    report.append("📈 股票投资组合标准化报告")
    report.append("=" * 120)
    report.append(f"📊 报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("-" * 120)
    
    # 今日详细持仓
    report.append("📋 今日详细持仓:")
    report.append(f"{'股票代码':<12} {'股票名称':<20} {'数量':<8} {'价格':<10} {'价值(CNY)':<12} {'币种':<8} {'平台':<15}")
    report.append("-" * 120)
    for holding in today_data['holdings']:
        report.append(f"{holding['code']:<12} {holding['name']:<20} {holding['quantity']:<8.1f} {holding['price']:<10.3f} {holding['value_cny']:<12.2f} {holding['currency']:<8} {holding['platform']:<15}")
    
    report.append("-" * 120)
    report.append(f"💰 今日总资产: {today_total:.2f} CNY")
    report.append("")
    
    # 三重对比
    report.append("🔄 三重时间维度对比:")
    report.append(f"   年初 ({year_start_data['date']}): {year_start_total:.2f} CNY")
    report.append(f"   昨日 ({yesterday_data['date']}): {yesterday_total:.2f} CNY") 
    report.append(f"   今日 ({today_data['date']}): {today_total:.2f} CNY")
    report.append("")
    
    # 变化分析
    report.append("📊 变化分析:")
    report.append(f"   今日 vs 昨日: {change_vs_yesterday:+.2f} CNY ({change_pct_vs_yesterday:+.2f}%)")
    report.append(f"   今日 vs 年初: {change_vs_year_start:+.2f} CNY ({change_pct_vs_year_start:+.2f}%)")
    report.append("")
    
    # 波动解读
    report.append("🎯 波动解读:")
    if abs(change_pct_vs_yesterday) > 1.0:
        if change_vs_yesterday > 0:
            report.append("   今日投资组合表现强劲，主要受益于市场整体上涨。")
        else:
            report.append("   今日投资组合出现回调，主要受市场短期调整影响。")
    else:
        report.append("   今日投资组合波动较小，保持相对稳定。")
    
    report.append("=" * 120)
    
    return "\n".join(report)

def main():
    try:
        portfolio_data, exchange_rate = get_latest_data()
        report = format_report(portfolio_data, exchange_rate)
        print(report)
    except Exception as e:
        print(f"生成报告时出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()