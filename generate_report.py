#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite股票投资组合报告生成器
"""

import sqlite3
import datetime
from decimal import Decimal, ROUND_HALF_UP

def format_decimal(value, places=2):
    """格式化小数，四舍五入"""
    if value is None:
        return "N/A"
    decimal_value = Decimal(str(value))
    rounded = decimal_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return float(rounded)

def generate_portfolio_report():
    """生成投资组合报告"""
    conn = sqlite3.connect('stock_portfolio.db')
    cursor = conn.cursor()
    
    # 获取当前日期
    today = datetime.date.today().strftime('%Y-%m-%d')
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 获取所有持仓
    cursor.execute("""
        SELECT code, name, quantity, currency, platform 
        FROM holdings 
        WHERE quantity > 0
    """)
    holdings = cursor.fetchall()
    
    if not holdings:
        print("📊 没有找到任何持仓记录")
        conn.close()
        return
    
    # 获取今日价格
    total_value_cny = 0.0
    portfolio_data = []
    
    for holding in holdings:
        code, name, quantity, currency, platform = holding
        
        # 查询今日价格
        cursor.execute("""
            SELECT price FROM stock_prices 
            WHERE code = ? AND date = ?
            ORDER BY created_at DESC LIMIT 1
        """, (code, today))
        
        price_row = cursor.fetchone()
        current_price = price_row[0] if price_row else None
        
        if current_price is not None:
            holding_value = quantity * current_price
            if currency == 'USD':
                # 这里简化处理，假设汇率为7.2
                exchange_rate = 7.2
                holding_value_cny = holding_value * exchange_rate
                total_value_cny += holding_value_cny
            else:
                holding_value_cny = holding_value
                total_value_cny += holding_value_cny
        else:
            holding_value_cny = None
        
        portfolio_data.append({
            'code': code,
            'name': name,
            'quantity': quantity,
            'currency': currency,
            'current_price': current_price,
            'holding_value': holding_value_cny,
            'platform': platform
        })
    
    # 生成报告
    print("=" * 100)
    print("📈 股票投资组合汇总报告 (SQLite版本)")
    print("=" * 100)
    print("📊 报告时间: {}".format(now))
    print("-" * 100)
    print("{:<12} {:<15} {:<12} {:<12} {:<12} {:<8} {:<12}".format(
        "股票代码", "股票名称", "持仓数量", "当前价格", "持仓价值", "币种", "平台"
    ))
    print("-" * 100)
    
    for item in portfolio_data:
        price_str = "{:.3f}".format(item['current_price']) if item['current_price'] is not None else "N/A"
        value_str = "{:.2f}".format(item['holding_value']) if item['holding_value'] is not None else "N/A"
        print("{:<12} {:<15} {:<12} {:<12} {:<12} {:<8} {:<12}".format(
            item['code'], item['name'], item['quantity'], 
            price_str, value_str, item['currency'], item['platform']
        ))
    
    print("-" * 100)
    print("💰 总资产价值: {:.2f} CNY".format(total_value_cny))
    print("=" * 100)
    
    # 保存到历史记录
    cursor.execute("""
        INSERT OR REPLACE INTO portfolio_values 
        (date, total_value_cny, total_value_usd, created_at)
        VALUES (?, ?, ?, ?)
    """, (today, total_value_cny, total_value_cny/7.2 if total_value_cny > 0 else 0, now))
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    generate_portfolio_report()