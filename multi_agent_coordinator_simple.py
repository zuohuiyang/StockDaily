#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的多智能体协调器 - 直接函数调用
"""

import json
import sys
from datetime import datetime
import sqlite3

# 导入智能体模块
from investment_analyst_agent import analyze_portfolio
from performance_monitor_agent import monitor_performance  
from report_generator_agent import generate_report

def get_portfolio_data():
    """获取投资组合数据"""
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    
    # 获取最新日期的数据
    cursor.execute('SELECT date FROM stock_prices ORDER BY date DESC LIMIT 1')
    latest_date = cursor.fetchone()[0]
    
    # 获取持仓信息
    cursor.execute('SELECT code, name, quantity, currency, platform FROM holdings')
    holdings = cursor.fetchall()
    
    portfolio_data = {
        'date': latest_date,
        'holdings': []
    }
    
    for code, name, quantity, currency, platform in holdings:
        cursor.execute('SELECT price FROM stock_prices WHERE code = ? AND date = ?', (code, latest_date))
        price_result = cursor.fetchone()
        price = price_result[0] if price_result else 0
        
        portfolio_data['holdings'].append({
            'code': code,
            'name': name,
            'quantity': quantity,
            'price': price,
            'currency': currency,
            'platform': platform
        })
    
    conn.close()
    return portfolio_data

def main():
    """主函数"""
    try:
        # 获取投资组合数据
        portfolio_data = get_portfolio_data()
        
        start_time = datetime.now()
        
        # 并行执行智能体（这里简化为顺序执行以避免复杂性）
        investment_result = analyze_portfolio(portfolio_data, 'comprehensive')
        performance_result = monitor_performance(portfolio_data, ['response_time', 'accuracy', 'resource_usage'])
        report_result = generate_report(portfolio_data, 'daily_investment_report', 'markdown_with_tables')
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # 汇总结果
        comprehensive_result = {
            'timestamp': datetime.now().isoformat(),
            'execution_time_total': execution_time,
            'agents_results': {
                'investment_analyst': {
                    'success': True,
                    'data': investment_result
                },
                'performance_monitor': {
                    'success': True, 
                    'data': performance_result
                },
                'report_generator': {
                    'success': True,
                    'data': report_result
                }
            },
            'success': True
        }
        
        print(json.dumps(comprehensive_result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        error_result = {
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'success': False
        }
        print(json.dumps(error_result, indent=2, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()