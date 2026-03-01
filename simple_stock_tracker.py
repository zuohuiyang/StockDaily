#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单股票价格查询器 - 专门处理A股ETF
"""

import requests
import json
import time
from datetime import datetime

def get_a_stock_price(stock_code):
    """
    获取A股股票/ETF价格
    使用新浪财经接口
    """
    # 新浪财经API格式：http://hq.sinajs.cn/list=sh518850
    prefix = "sh" if stock_code.startswith(('6', '5')) else "sz"
    url = f"http://hq.sinajs.cn/list={prefix}{stock_code}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            # 解析返回的数据
            data = response.text.strip()
            if "var hq_str_" in data:
                # 提取实际数据部分
                parts = data.split('"')[1].split(',')
                if len(parts) > 3:
                    current_price = float(parts[3])  # 当前价格在第4个位置
                    stock_name = parts[0]  # 股票名称
                    return {
                        'name': stock_name,
                        'price': current_price,
                        'code': stock_code
                    }
    except Exception as e:
        print(f"获取股票 {stock_code} 价格时出错: {e}")
    
    return None

def calculate_portfolio_value(holdings):
    """
    计算投资组合价值
    holdings: [{'code': '518850', 'shares': 1, 'currency': 'CNY'}]
    """
    total_value = 0
    portfolio_details = []
    
    for holding in holdings:
        stock_info = get_a_stock_price(holding['code'])
        if stock_info:
            value = stock_info['price'] * holding['shares']
            total_value += value
            
            portfolio_details.append({
                '股票代码': holding['code'],
                '股票名称': stock_info['name'],
                '持仓数量': holding['shares'],
                '当前价格': f"{stock_info['price']:.3f}",
                '持仓价值': f"{value:.2f}",
                '币种': holding['currency']
            })
        else:
            portfolio_details.append({
                '股票代码': holding['code'],
                '股票名称': '未知',
                '持仓数量': holding['shares'],
                '当前价格': '获取失败',
                '持仓价值': 'N/A',
                '币种': holding['currency']
            })
    
    return portfolio_details, total_value

def print_portfolio_table(portfolio_details, total_value):
    """
    打印投资组合表格
    """
    print("=" * 80)
    print("📈 股票投资组合汇总")
    print("=" * 80)
    print(f"{'股票代码':<10} {'股票名称':<15} {'持仓数量':<10} {'当前价格':<12} {'持仓价值':<12} {'币种':<8}")
    print("-" * 80)
    
    for detail in portfolio_details:
        print(f"{detail['股票代码']:<10} {detail['股票名称']:<15} {detail['持仓数量']:<10} {detail['当前价格']:<12} {detail['持仓价值']:<12} {detail['币种']:<8}")
    
    print("-" * 80)
    print(f"{'总计':<50} {total_value:.2f} CNY")
    print("=" * 80)

def main():
    # 你的持仓信息
    holdings = [
        {
            'code': '518850',
            'shares': 1,
            'currency': 'CNY'
        }
    ]
    
    print(f"📊 查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    portfolio_details, total_value = calculate_portfolio_value(holdings)
    print_portfolio_table(portfolio_details, total_value)

if __name__ == "__main__":
    main()