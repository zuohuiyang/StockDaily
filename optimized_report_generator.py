#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化的投资组合报告生成器 - 高性能版本
减少数据库查询次数，缓存结果，提高响应速度
"""

import sqlite3
from datetime import datetime, timedelta
import json
import os

class OptimizedReportGenerator:
    def __init__(self, db_path='portfolio.db'):
        self.db_path = db_path
        self.cache = {}
        
    def get_cached_data(self, key):
        """从缓存获取数据"""
        return self.cache.get(key)
    
    def set_cached_data(self, key, data):
        """设置缓存数据"""
        self.cache[key] = data
    
    def get_exchange_rate(self):
        """获取最新汇率，带缓存"""
        cache_key = 'exchange_rate'
        cached = self.get_cached_data(cache_key)
        if cached is not None:
            return cached
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT rate FROM exchange_rates WHERE from_currency = "USD" AND to_currency = "CNY" ORDER BY date DESC LIMIT 1')
        rate_result = cursor.fetchone()
        exchange_rate = rate_result[0] if rate_result else 6.8803
        conn.close()
        
        self.set_cached_data(cache_key, exchange_rate)
        return exchange_rate
    
    def get_all_dates(self):
        """获取所有可用日期"""
        cache_key = 'all_dates'
        cached = self.get_cached_data(cache_key)
        if cached is not None:
            return cached
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT date FROM stock_prices ORDER BY date DESC')
        dates = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        self.set_cached_data(cache_key, dates)
        return dates
    
    def get_holdings(self):
        """获取所有持仓信息"""
        cache_key = 'holdings'
        cached = self.get_cached_data(cache_key)
        if cached is not None:
            return cached
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT code, name, quantity, currency, platform FROM holdings')
        holdings = cursor.fetchall()
        conn.close()
        
        self.set_cached_data(cache_key, holdings)
        return holdings
    
    def get_prices_for_date(self, target_date):
        """获取指定日期的所有价格，批量查询"""
        cache_key = f'prices_{target_date}'
        cached = self.get_cached_data(cache_key)
        if cached is not None:
            return cached
            
        holdings = self.get_holdings()
        codes = [holding[0] for holding in holdings]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 批量查询所有价格
        price_dict = {}
        for code in codes:
            cursor.execute('SELECT price FROM stock_prices WHERE code = ? AND date = ?', (code, target_date))
            result = cursor.fetchone()
            price_dict[code] = result[0] if result else 0
        
        conn.close()
        self.set_cached_data(cache_key, price_dict)
        return price_dict
    
    def calculate_portfolio_value(self, date):
        """计算指定日期的投资组合价值"""
        cache_key = f'portfolio_value_{date}'
        cached = self.get_cached_data(cache_key)
        if cached is not None:
            return cached
            
        holdings = self.get_holdings()
        prices = self.get_prices_for_date(date)
        exchange_rate = self.get_exchange_rate()
        
        total_value = 0
        holdings_detail = []
        
        for code, name, quantity, currency, platform in holdings:
            price = prices.get(code, 0)
            if currency == 'CNY':
                value_cny = price * quantity
            else:  # USD
                value_usd = price * quantity
                value_cny = value_usd * exchange_rate
            
            holdings_detail.append({
                'code': code,
                'name': name,
                'quantity': quantity,
                'price': price,
                'value_cny': value_cny,
                'currency': currency,
                'platform': platform
            })
            total_value += value_cny
        
        result = {
            'date': date,
            'total': total_value,
            'holdings': holdings_detail
        }
        
        self.set_cached_data(cache_key, result)
        return result
    
    def get_today_date(self):
        """获取今天的日期（从数据库中获取最新日期）"""
        dates = self.get_all_dates()
        return dates[0] if dates else datetime.now().strftime('%Y-%m-%d')
    
    def get_yesterday_date(self, today_date):
        """获取昨天的日期"""
        dates = self.get_all_dates()
        try:
            today_index = dates.index(today_date)
            if today_index + 1 < len(dates):
                return dates[today_index + 1]
            else:
                # 如果没有昨天的数据，使用年初数据
                return '2026-01-02'
        except ValueError:
            return '2026-01-02'
    
    def generate_report(self):
        """生成优化的报告"""
        today_date = self.get_today_date()
        yesterday_date = self.get_yesterday_date(today_date)
        year_start_date = '2026-01-02'
        
        # 并行获取所有需要的数据
        today_data = self.calculate_portfolio_value(today_date)
        yesterday_data = self.calculate_portfolio_value(yesterday_date)
        year_start_data = self.calculate_portfolio_value(year_start_date)
        
        # 计算变化
        today_total = today_data['total']
        yesterday_total = yesterday_data['total']
        year_start_total = year_start_data['total']
        
        change_vs_yesterday = today_total - yesterday_total
        change_pct_vs_yesterday = (change_vs_yesterday / yesterday_total) * 100 if yesterday_total > 0 else 0
        
        change_vs_year_start = today_total - year_start_total
        change_pct_vs_year_start = (change_vs_year_start / year_start_total) * 100 if year_start_total > 0 else 0
        
        # 生成报告
        report_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return {
            'report_time': report_time,
            'today_data': today_data,
            'yesterday_data': yesterday_data,
            'year_start_data': year_start_data,
            'change_vs_yesterday': change_vs_yesterday,
            'change_pct_vs_yesterday': change_pct_vs_yesterday,
            'change_vs_year_start': change_vs_year_start,
            'change_pct_vs_year_start': change_pct_vs_year_start
        }

def format_report_to_template(report_data):
    """按照约定模板格式化报告"""
    today_data = report_data['today_data']
    yesterday_data = report_data['yesterday_data']
    year_start_data = report_data['year_start_data']
    
    # 表格数据
    table_rows = []
    for holding in today_data['holdings']:
        table_rows.append(f"| {holding['code']} | {holding['name']} | {holding['quantity']:.1f} | {holding['price']:.3f} | {holding['value_cny']:.2f} | {holding['currency']} | {holding['platform']} |")
    
    # 总资产对比
    today_total = today_data['total']
    yesterday_total = yesterday_data['total']
    year_start_total = year_start_data['total']
    
    change_vs_yesterday = report_data['change_vs_yesterday']
    change_pct_vs_yesterday = report_data['change_pct_vs_yesterday']
    change_vs_year_start = report_data['change_vs_year_start']
    change_pct_vs_year_start = report_data['change_pct_vs_year_start']
    
    # 波动解读
    if abs(change_pct_vs_yesterday) > 1.0:
        if change_vs_yesterday > 0:
            analysis = "今日投资组合表现强劲，主要受益于市场整体上涨。"
        else:
            analysis = "今日投资组合出现回调，主要受市场短期调整影响。"
    else:
        analysis = "今日投资组合波动较小，保持相对稳定。"
    
    report = f"""# 📈 股票投资组合日报

📊 报告时间: {report_data['report_time']}

## 📅 今日持仓详情
| 股票代码 | 股票名称 | 持仓数量 | 当前价格 | 持仓价值 | 币种 | 平台 |
|----------|----------|----------|----------|----------|------|------|
{chr(10).join(table_rows)}

## 💰 总资产对比
| 对比维度 | 时间 | 总资产(CNY) | 变化金额 | 变化幅度 |
|----------|------|-------------|----------|----------|
| **今日 vs 昨日** | {yesterday_data['date']} → {today_data['date']} | {yesterday_total:.2f} → {today_total:.2f} | {change_vs_yesterday:+.2f} | {change_pct_vs_yesterday:+.2f}% |
| **今日 vs 年初** | {year_start_data['date']} → {today_data['date']} | {year_start_total:.2f} → {today_total:.2f} | {change_vs_year_start:+.2f} | {change_pct_vs_year_start:+.2f}% |

## 🎯 今日波动解读
{analysis}"""
    
    return report

def main():
    try:
        generator = OptimizedReportGenerator()
        report_data = generator.generate_report()
        formatted_report = format_report_to_template(report_data)
        print(formatted_report)
    except Exception as e:
        print(f"生成报告时出错: {e}")

if __name__ == "__main__":
    main()