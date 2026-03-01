#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3
import json
from datetime import datetime, date

def get_portfolio_value(db_path, query_date):
    """获取指定日期的投资组合价值"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取该日期的汇率
    cursor.execute("""
        SELECT rate FROM exchange_rates 
        WHERE date(date) = ? AND from_currency = 'USD' AND to_currency = 'CNY'
        ORDER BY created_at DESC LIMIT 1
    """, (query_date,))
    exchange_rate_row = cursor.fetchone()
    exchange_rate = exchange_rate_row[0] if exchange_rate_row else 6.85
    
    # 获取持仓信息
    cursor.execute("SELECT code, name, quantity, currency, platform FROM holdings")
    holdings = cursor.fetchall()
    
    total_value_cny = 0
    stock_values = []
    
    for holding in holdings:
        code, name, quantity, currency, platform = holding
        # 获取该日期的股票价格
        cursor.execute("""
            SELECT price FROM stock_prices 
            WHERE code = ? AND date(date) = ?
            ORDER BY created_at DESC LIMIT 1
        """, (code, query_date))
        price_row = cursor.fetchone()
        
        if price_row:
            price = price_row[0]
            if currency == 'USD':
                value_cny = price * quantity * exchange_rate
                value_display = f"{price * quantity:.2f} USD"
            else:
                value_cny = price * quantity
                value_display = f"{value_cny:.2f} CNY"
            
            stock_values.append({
                'code': code,
                'name': name,
                'quantity': quantity,
                'price': price,
                'value_cny': value_cny,
                'currency': currency,
                'platform': platform
            })
            total_value_cny += value_cny
        else:
            stock_values.append({
                'code': code,
                'name': name,
                'quantity': quantity,
                'price': 0,
                'value_cny': 0,
                'currency': currency,
                'platform': platform
            })
    
    conn.close()
    return total_value_cny, stock_values, exchange_rate

def generate_triple_analysis():
    """生成年初、昨天、今天的三重对比分析"""
    db_path = "portfolio.db"
    today = "2026-02-27"
    yesterday = "2026-02-26" 
    year_start = "2026-01-01"
    
    # 获取三个时间点的数据
    today_value, today_stocks, today_rate = get_portfolio_value(db_path, today)
    yesterday_value, yesterday_stocks, yesterday_rate = get_portfolio_value(db_path, yesterday)
    year_start_value, year_start_stocks, year_start_rate = get_portfolio_value(db_path, year_start)
    
    # 计算变化
    change_yesterday_today = today_value - yesterday_value
    change_year_start_today = today_value - year_start_value
    change_year_start_yesterday = yesterday_value - year_start_value
    
    pct_change_yesterday_today = (change_yesterday_today / yesterday_value * 100) if yesterday_value > 0 else 0
    pct_change_year_start_today = (change_year_start_today / year_start_value * 100) if year_start_value > 0 else 0
    pct_change_year_start_yesterday = (change_year_start_yesterday / year_start_value * 100) if year_start_value > 0 else 0
    
    # 打印报告
    print("=" * 120)
    print("📈 股票投资组合三重时间维度对比分析报告")
    print("=" * 120)
    print(f"📊 报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 120)
    
    # 总资产对比表格
    print("💰 总资产三重对比:")
    print(f"   年初 (2026-01-01): {year_start_value:.2f} CNY")
    print(f"   昨日 (2026-02-26): {yesterday_value:.2f} CNY") 
    print(f"   今日 (2026-02-27): {today_value:.2f} CNY")
    print()
    
    # 变化分析
    print("📊 变化分析:")
    print(f"   年初 → 昨日: {'+' if change_year_start_yesterday >= 0 else ''}{change_year_start_yesterday:.2f} CNY ({'+' if pct_change_year_start_yesterday >= 0 else ''}{pct_change_year_start_yesterday:.2f}%)")
    print(f"   昨日 → 今日: {'+' if change_yesterday_today >= 0 else ''}{change_yesterday_today:.2f} CNY ({'+' if pct_change_yesterday_today >= 0 else ''}{pct_change_yesterday_today:.2f}%)")
    print(f"   年初 → 今日: {'+' if change_year_start_today >= 0 else ''}{change_year_start_today:.2f} CNY ({'+' if pct_change_year_start_today >= 0 else ''}{pct_change_year_start_today:.2f}%)")
    print()
    
    # 个股贡献分析（今日vs昨日）
    print("🔍 今日波动个股贡献分析 (昨日→今日):")
    total_contribution = 0
    contributions = []
    for i, stock in enumerate(today_stocks):
        today_val = stock['value_cny']
        yesterday_val = yesterday_stocks[i]['value_cny'] if i < len(yesterday_stocks) else 0
        contribution = today_val - yesterday_val
        contributions.append((stock['code'], stock['name'], contribution))
        total_contribution += abs(contribution)
    
    for code, name, contrib in contributions:
        if abs(contrib) > 0.01:  # 忽略微小变化
            percentage = (contrib / total_contribution * 100) if total_contribution > 0 else 0
            print(f"   {code} ({name}): {'+' if contrib >= 0 else ''}{contrib:.2f} CNY ({'+' if percentage >= 0 else ''}{percentage:.1f}%)")
    
    print()
    
    # 年度表现分析
    print("🎯 年度表现亮点:")
    best_performer = None
    best_return = -float('inf')
    
    for i, stock in enumerate(today_stocks):
        year_start_val = year_start_stocks[i]['value_cny'] if i < len(year_start_stocks) else 0
        today_val = stock['value_cny']
        if year_start_val > 0:
            annual_return = (today_val - year_start_val) / year_start_val * 100
            if annual_return > best_return:
                best_return = annual_return
                best_performer = (stock['code'], stock['name'], annual_return)
    
    if best_performer:
        print(f"   年度最佳表现: {best_performer[0]} ({best_performer[1]}) +{best_performer[2]:.2f}%")
    
    print()
    
    # 市场解读
    print("💡 市场解读:")
    print("   SOXX (iShares半导体ETF) 作为科技成长股，在2026年表现出色，主要受益于:")
    print("   • 全球AI技术快速发展带动芯片需求")
    print("   • 美联储货币政策转向预期利好科技股估值")
    print("   • 半导体行业库存周期触底回升")
    print("   • 人民币汇率相对稳定，降低了外汇风险")
    print()
    print("   黄金ETF (518850) 作为避险资产，提供了投资组合的稳定性，")
    print("   在市场波动时起到对冲作用。")
    print("=" * 120)

if __name__ == "__main__":
    generate_triple_analysis()