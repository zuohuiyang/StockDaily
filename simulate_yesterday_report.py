#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟昨天早上5:30的报告生成
基于2026-02-26收盘数据
"""

import sqlite3
from datetime import datetime

def generate_yesterday_report():
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    
    # 获取2026-02-26的数据
    report_date = '2026-02-26'
    
    # 获取汇率
    cursor.execute('SELECT rate FROM exchange_rates WHERE date = ? ORDER BY created_at DESC LIMIT 1', (report_date,))
    exchange_rate_result = cursor.fetchone()
    exchange_rate = exchange_rate_result[0] if exchange_rate_result else 6.8803
    
    # 获取所有持仓和对应价格
    cursor.execute('''
        SELECT h.code, h.name, h.quantity, h.currency, h.platform, sp.price
        FROM holdings h
        LEFT JOIN stock_prices sp ON h.code = sp.code AND sp.date = ?
        ORDER BY h.currency DESC, h.code
    ''', (report_date,))
    
    holdings = cursor.fetchall()
    
    # 计算总资产
    total_value = 0
    holdings_data = []
    
    for code, name, quantity, currency, platform, price in holdings:
        if price is None:
            price = 0
        if currency == 'CNY':
            value_cny = price * quantity
        else:  # USD
            value_cny = price * quantity * exchange_rate
        total_value += value_cny
        
        holdings_data.append({
            'code': code,
            'name': name,
            'quantity': quantity,
            'price': price,
            'value_cny': value_cny,
            'currency': currency,
            'platform': platform
        })
    
    conn.close()
    
    # 生成报告
    print("=" * 120)
    print("📈 股票投资组合模拟报告 (2026-02-26 收盘)")
    print("=" * 120)
    print(f"📊 模拟生成时间: 2026-02-27 05:30:00")
    print("-" * 120)
    print("📋 详细持仓:")
    print(f"{'股票代码':<12} {'股票名称':<20} {'数量':<8} {'价格':<10} {'价值(CNY)':<12} {'币种':<8} {'平台':<15}")
    print("-" * 120)
    
    for holding in holdings_data:
        print(f"{holding['code']:<12} {holding['name']:<20} {holding['quantity']:<8.1f} {holding['price']:<10.3f} {holding['value_cny']:<12.2f} {holding['currency']:<8} {holding['platform']:<15}")
    
    print("-" * 120)
    print(f"💰 总资产: {total_value:.2f} CNY")
    print(f"💱 汇率: 1 USD = {exchange_rate:.4f} CNY")
    print("=" * 120)

if __name__ == "__main__":
    generate_yesterday_report()