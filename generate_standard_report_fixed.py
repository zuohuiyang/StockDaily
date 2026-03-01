#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标准化投资组合报告生成器 (Python 3.6 兼容版)
按照统一模板生成每日报告
"""

import sqlite3
from datetime import datetime

def get_exchange_rate():
    """获取最新汇率"""
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    cursor.execute('SELECT rate FROM exchange_rates WHERE from_currency = "USD" AND to_currency = "CNY" ORDER BY date DESC LIMIT 1')
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 6.8803

def get_stock_price(code, date):
    """获取指定股票在指定日期的价格"""
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    cursor.execute('SELECT price FROM stock_prices WHERE code = ? AND date = ?', (code, date))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def get_holdings():
    """获取所有持仓"""
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    cursor.execute('SELECT code, name, quantity, currency, platform FROM holdings')
    holdings = cursor.fetchall()
    conn.close()
    return holdings

def calculate_portfolio_value(holdings, target_date, exchange_rate):
    """计算指定日期的投资组合价值"""
    total_value = 0
    detailed_holdings = []
    
    for code, name, quantity, currency, platform in holdings:
        price = get_stock_price(code, target_date)
        if currency == 'CNY':
            value_cny = price * quantity
        else:  # USD
            value_cny = price * quantity * exchange_rate
        
        detailed_holdings.append({
            'code': code,
            'name': name,
            'quantity': quantity,
            'price': price,
            'value_cny': value_cny,
            'currency': currency,
            'platform': platform
        })
        total_value += value_cny
    
    return total_value, detailed_holdings

def main():
    # 配置日期
    today = '2026-02-27'
    yesterday = '2026-02-26'
    year_start = '2026-01-02'
    
    # 获取基础数据
    exchange_rate = get_exchange_rate()
    holdings = get_holdings()
    
    # 计算各时间点的价值
    today_total, today_holdings = calculate_portfolio_value(holdings, today, exchange_rate)
    yesterday_total, yesterday_holdings = calculate_portfolio_value(holdings, yesterday, exchange_rate)
    year_start_total, year_start_holdings = calculate_portfolio_value(holdings, year_start, exchange_rate)
    
    # 计算变化
    change_vs_yesterday = today_total - yesterday_total
    change_pct_vs_yesterday = (change_vs_yesterday / yesterday_total) * 100 if yesterday_total > 0 else 0
    
    change_vs_year_start = today_total - year_start_total
    change_pct_vs_year_start = (change_vs_year_start / year_start_total) * 100 if year_start_total > 0 else 0
    
    # 生成标准化报告
    print("=" * 120)
    print("📈 股票投资组合标准化报告")
    print("=" * 120)
    print("📊 报告时间: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    print("-" * 120)
    
    # 今日详细持仓
    print("📋 今日详细持仓:")
    print("{:<12} {:<20} {:<8} {:<10} {:<12} {:<8} {:<15}".format(
        "股票代码", "股票名称", "数量", "价格", "价值(CNY)", "币种", "平台"))
    print("-" * 120)
    for holding in today_holdings:
        print("{:<12} {:<20} {:<8.1f} {:<10.3f} {:<12.2f} {:<8} {:<15}".format(
            holding['code'], holding['name'], holding['quantity'], 
            holding['price'], holding['value_cny'], holding['currency'], holding['platform']))
    
    print("-" * 120)
    print("💰 今日总资产: {:.2f} CNY".format(today_total))
    print("")
    
    # 三重对比
    print("🔄 三重时间维度对比:")
    print("   年初 ({}): {:.2f} CNY".format(year_start, year_start_total))
    print("   昨日 ({}): {:.2f} CNY".format(yesterday, yesterday_total))
    print("   今日 ({}): {:.2f} CNY".format(today, today_total))
    print("")
    
    # 变化分析
    print("📊 变化分析:")
    print("   今日 vs 昨日: {:+.2f} CNY ({:+.2f}%)".format(change_vs_yesterday, change_pct_vs_yesterday))
    print("   今日 vs 年初: {:+.2f} CNY ({:+.2f}%)".format(change_vs_year_start, change_pct_vs_year_start))
    print("")
    
    # 波动解读
    print("🎯 波动解读:")
    if abs(change_pct_vs_yesterday) > 1.0:
        if change_vs_yesterday > 0:
            print("   今日投资组合表现强劲，主要受益于市场整体上涨。")
        else:
            print("   今日投资组合出现回调，主要受市场短期调整影响。")
    else:
        print("   今日投资组合波动较小，保持相对稳定。")
    
    print("=" * 120)

if __name__ == "__main__":
    main()