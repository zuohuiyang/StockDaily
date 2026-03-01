#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from datetime import datetime, timedelta
import json

def get_portfolio_data(date_str):
    """获取指定日期的投资组合数据"""
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    
    # 获取持仓信息
    cursor.execute("SELECT code, name, quantity, currency, platform FROM holdings")
    holdings = cursor.fetchall()
    
    total_cny = 0
    total_usd = 0
    stock_details = []
    
    for code, name, quantity, currency, platform in holdings:
        # 获取股票价格
        cursor.execute("""
            SELECT price FROM stock_prices 
            WHERE code = ? AND date(date) = date(?)
            ORDER BY created_at DESC LIMIT 1
        """, (code, date_str))
        price_row = cursor.fetchone()
        
        if price_row:
            price = price_row[0]
            value = quantity * price
            
            if currency == 'USD':
                # 获取汇率
                cursor.execute("""
                    SELECT rate FROM exchange_rates 
                    WHERE from_currency = 'USD' AND to_currency = 'CNY' 
                    AND date(date) = date(?)
                    ORDER BY created_at DESC LIMIT 1
                """, (date_str,))
                rate_row = cursor.fetchone()
                if rate_row:
                    rate = rate_row[0]
                    value_cny = value * rate
                    total_usd += value
                    total_cny += value_cny
                else:
                    rate = 6.88
                    value_cny = value * rate
                    total_usd += value
                    total_cny += value_cny
            else:
                value_cny = value
                total_cny += value_cny
            
            stock_details.append({
                'code': code,
                'name': name,
                'quantity': quantity,
                'price': price,
                'value': value,
                'value_cny': value_cny if currency == 'USD' else value,
                'currency': currency,
                'platform': platform
            })
        else:
            stock_details.append({
                'code': code,
                'name': name,
                'quantity': quantity,
                'price': 0,
                'value': 0,
                'value_cny': 0,
                'currency': currency,
                'platform': platform
            })
    
    conn.close()
    return {
        'total_cny': total_cny,
        'total_usd': total_usd,
        'stocks': stock_details,
        'date': date_str
    }

def analyze_changes(today_data, yesterday_data):
    """分析资产变化"""
    today_total = today_data['total_cny']
    yesterday_total = yesterday_data['total_cny']
    total_change = today_total - yesterday_total
    total_change_pct = (total_change / yesterday_total) * 100 if yesterday_total > 0 else 0
    
    # 分析各股票贡献
    stock_contributions = []
    for today_stock in today_data['stocks']:
        code = today_stock['code']
        yesterday_stock = None
        for stock in yesterday_data['stocks']:
            if stock['code'] == code:
                yesterday_stock = stock
                break
        
        if yesterday_stock:
            today_value_cny = today_stock['value_cny']
            yesterday_value_cny = yesterday_stock['value_cny']
            contribution = today_value_cny - yesterday_value_cny
            stock_contributions.append({
                'code': code,
                'name': today_stock['name'],
                'contribution': contribution,
                'today_value': today_value_cny,
                'yesterday_value': yesterday_value_cny
            })
    
    # 找出最大贡献者
    max_contributor = max(stock_contributions, key=lambda x: abs(x['contribution']))
    
    return {
        'total_change': total_change,
        'total_change_pct': total_change_pct,
        'stock_contributions': stock_contributions,
        'max_contributor': max_contributor
    }

def main():
    today = "2026-02-27"
    yesterday = "2026-02-26"
    
    today_data = get_portfolio_data(today)
    yesterday_data = get_portfolio_data(yesterday)
    
    analysis = analyze_changes(today_data, yesterday_data)
    
    print("=" * 120)
    print("📈 股票投资组合对比分析报告")
    print("=" * 120)
    print(f"📊 报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 120)
    print("💰 总资产对比:")
    print(f"   昨日总资产: {yesterday_data['total_cny']:.2f} CNY")
    print(f"   今日总资产: {today_data['total_cny']:.2f} CNY")
    print(f"   变化金额: {analysis['total_change']:+.2f} CNY")
    print(f"   变化幅度: {analysis['total_change_pct']:+.2f}%")
    print("-" * 120)
    print("🔍 个股贡献分析:")
    for contrib in analysis['stock_contributions']:
        change = contrib['contribution']
        print(f"   {contrib['code']} ({contrib['name']}): {change:+.2f} CNY")
    print("-" * 120)
    print("🎯 主要波动来源:")
    max_contrib = analysis['max_contributor']
    print(f"   {max_contrib['code']} ({max_contrib['name']}) 是主要波动来源")
    print(f"   贡献了 {max_contrib['contribution']:+.2f} CNY 的资产变化")
    print("-" * 120)
    print("💡 波动解读:")
    if max_contrib['code'] == 'SOXX':
        print("   SOXX (iShares半导体ETF) 作为科技股，受以下因素影响:")
        print("   • 全球半导体行业周期性波动")
        print("   • 美联储利率政策对科技股估值的影响") 
        print("   • 人工智能和芯片需求的市场预期")
        print("   • 美元汇率波动对海外投资者的影响")
    elif max_contrib['code'] == '518850':
        print("   518850 (华安黄金ETF) 作为避险资产，受以下因素影响:")
        print("   • 国际金价波动")
        print("   • 全球经济不确定性增加时的避险需求")
        print("   • 美元指数与黄金价格的负相关关系")
        print("   • 通胀预期对黄金保值功能的影响")
    print("=" * 120)

if __name__ == "__main__":
    main()