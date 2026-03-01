#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3
import datetime

def generate_report():
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    
    # 获取汇率
    cursor.execute("SELECT rate FROM exchange_rates WHERE from_currency = 'USD' AND to_currency = 'CNY' ORDER BY date DESC LIMIT 1")
    exchange_rate_row = cursor.fetchone()
    exchange_rate = exchange_rate_row[0] if exchange_rate_row else 6.85
    
    # 获取所有持仓和价格
    cursor.execute("""
        SELECT h.code, h.name, h.quantity, h.currency, h.platform, 
               p.price, p.date as price_date
        FROM holdings h
        LEFT JOIN stock_prices p ON h.code = p.code 
        WHERE p.date = (SELECT MAX(date) FROM stock_prices WHERE code = h.code)
        ORDER BY h.code
    """)
    holdings = cursor.fetchall()
    
    print("=" * 120)
    print("📈 股票投资组合汇总报告 (延迟数据版本)")
    print("=" * 120)
    print("📊 报告时间: {}".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    print("-" * 120)
    print("{:<12} {:<20} {:<12} {:<12} {:<15} {:<8} {:<15}".format(
        "股票代码", "股票名称", "持仓数量", "当前价格", "持仓价值", "币种", "平台"))
    print("-" * 120)
    
    total_cny = 0.0
    total_usd = 0.0
    
    for holding in holdings:
        code, name, quantity, currency, platform, price, price_date = holding
        if price is None:
            price = 0.0
        
        value = quantity * price
        
        if currency == 'CNY':
            total_cny += value
            value_str = "{:.2f}".format(value)
        else:
            total_usd += value
            value_str = "{:.2f}".format(value)
        
        print("{:<12} {:<20} {:<12.1f} {:<12.3f} {:<15} {:<8} {:<15}".format(
            code, name, quantity, price, value_str, currency, platform))
    
    print("-" * 120)
    print("💰 美元资产: {:.2f} USD".format(total_usd))
    print("💰 人民币资产: {:.2f} CNY".format(total_cny))
    
    usd_to_cny = total_usd * exchange_rate
    print("💱 美元转换为人民币: {:.2f} CNY (汇率: {:.4f})".format(usd_to_cny, exchange_rate))
    
    total_all_cny = total_cny + usd_to_cny
    print("💎 总资产 (人民币): {:.2f} CNY".format(total_all_cny))
    print("=" * 120)
    
    conn.close()

if __name__ == "__main__":
    generate_report()