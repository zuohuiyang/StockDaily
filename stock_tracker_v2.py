#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票资产追踪器 v2 - 支持手动价格输入作为备用
"""
import json
import time
from datetime import datetime
import requests

def get_stock_price_fallback(stock_code, manual_prices=None):
    """获取股票价格的备用方法"""
    if manual_prices and stock_code in manual_prices:
        return manual_prices[stock_code]
    
    # 如果是A股代码（6位数字）
    if stock_code.isdigit() and len(stock_code) == 6:
        # 尝试不同的数据源
        sources = [
            f"http://qt.gtimg.cn/q=sz{stock_code}" if stock_code.startswith(('0', '3')) else f"http://qt.gtimg.cn/q=sh{stock_code}",
            f"https://hq.sinajs.cn/list={stock_code}"
        ]
        
        for source in sources:
            try:
                response = requests.get(source, timeout=5)
                if response.status_code == 200:
                    content = response.text
                    # 解析腾讯财经格式: v_sh518850="1~黄金ETF~5.188~5.190~..."
                    if '="' in content:
                        parts = content.split('"')[1].split('~')
                        if len(parts) > 3:
                            try:
                                return float(parts[3])  # 最新价格
                            except (ValueError, IndexError):
                                continue
                    # 解析新浪财经格式
                    elif '="' not in content and '=' in content:
                        parts = content.split('=')[1].strip('";').split(',')
                        if len(parts) > 3:
                            try:
                                return float(parts[3])  # 最新价格
                            except (ValueError, IndexError):
                                continue
            except Exception as e:
                print(f"尝试 {source} 失败: {e}")
                continue
    
    return None

def load_portfolio():
    """加载投资组合配置"""
    try:
        with open('portfolio_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"holdings": [], "manual_prices": {}}

def calculate_portfolio():
    """计算投资组合价值"""
    portfolio = load_portfolio()
    holdings = portfolio.get("holdings", [])
    manual_prices = portfolio.get("manual_prices", {})
    
    total_value_cny = 0.0
    results = []
    
    print(f"📊 查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("📈 股票投资组合汇总")
    print("=" * 80)
    print(f"{'股票代码':<12} {'股票名称':<15} {'持仓数量':<12} {'当前价格':<12} {'持仓价值':<12} {'币种':<10}")
    print("-" * 80)
    
    for holding in holdings:
        stock_code = holding["code"]
        stock_name = holding.get("name", "未知")
        quantity = holding["quantity"]
        currency = holding.get("currency", "CNY")
        
        # 获取价格
        price = get_stock_price_fallback(stock_code, manual_prices)
        
        if price is not None:
            value = price * quantity
            if currency == "USD":
                # 这里需要汇率，暂时假设为7.2
                exchange_rate = 7.2
                value_cny = value * exchange_rate
                total_value_cny += value_cny
                print(f"{stock_code:<12} {stock_name:<15} {quantity:<12} {price:<12.3f} {value_cny:<12.2f} {currency:<10}")
            else:
                total_value_cny += value
                print(f"{stock_code:<12} {stock_name:<15} {quantity:<12} {price:<12.3f} {value:<12.2f} {currency:<10}")
        else:
            print(f"{stock_code:<12} {stock_name:<15} {quantity:<12} {'获取失败':<12} {'N/A':<12} {currency:<10}")
    
    print("-" * 80)
    print(f"总计                                                 {total_value_cny:.2f} CNY")
    print("=" * 80)

if __name__ == "__main__":
    calculate_portfolio()