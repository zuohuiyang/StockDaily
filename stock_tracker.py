#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票资产追踪器 - 简单版本
支持A股ETF基金查询（如518850）
"""

import json
import requests
import pandas as pd
from datetime import datetime
import os

class StockTracker:
    def __init__(self, config_file="portfolio.json"):
        self.config_file = config_file
        self.portfolio = self.load_portfolio()
    
    def load_portfolio(self):
        """加载投资组合配置"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 默认示例配置
            return {
                "holdings": [
                    {
                        "symbol": "518850",
                        "name": "黄金ETF",
                        "quantity": 1,
                        "platform": "银河证券",
                        "currency": "CNY"
                    }
                ]
            }
    
    def save_portfolio(self):
        """保存投资组合配置"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.portfolio, f, ensure_ascii=False, indent=2)
    
    def get_a_stock_price(self, symbol):
        """
        获取A股/ETF价格 - 使用新浪财经接口
        """
        try:
            # 新浪财经API格式：http://hq.sinajs.cn/list=sh518850
            prefix = "sh" if symbol.startswith(('6', '5')) else "sz"
            url = f"http://hq.sinajs.cn/list={prefix}{symbol}"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # 解析返回的数据
                data = response.text.strip()
                if "var hq_str_" in data:
                    # 提取价格数据
                    parts = data.split('"')[1].split(',')
                    if len(parts) > 3:
                        current_price = float(parts[3])  # 当前价格在第4个位置
                        return current_price
            return None
        except Exception as e:
            print(f"获取股票 {symbol} 价格失败: {e}")
            return None
    
    def get_exchange_rate(self):
        """
        获取美元兑人民币汇率 - 使用免费API
        """
        try:
            # 使用fixer.io的免费替代方案
            url = "https://api.exchangerate-api.com/v4/latest/USD"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data['rates']['CNY']
            return 7.2  # 默认汇率
        except Exception as e:
            print(f"获取汇率失败: {e}")
            return 7.2
    
    def calculate_portfolio_value(self):
        """计算投资组合总价值"""
        total_value_cny = 0
        holdings_data = []
        
        exchange_rate = self.get_exchange_rate()
        
        for holding in self.portfolio['holdings']:
            symbol = holding['symbol']
            quantity = holding['quantity']
            platform = holding['platform']
            currency = holding['currency']
            name = holding.get('name', symbol)
            
            # 获取当前价格
            current_price = self.get_a_stock_price(symbol)
            
            if current_price is not None:
                # 计算持仓价值
                holding_value = current_price * quantity
                
                # 如果是美元，转换为人民币
                if currency.upper() == 'USD':
                    holding_value_cny = holding_value * exchange_rate
                else:
                    holding_value_cny = holding_value
                    exchange_rate = 1.0  # 人民币不需要汇率
                
                total_value_cny += holding_value_cny
                
                holdings_data.append({
                    'symbol': symbol,
                    'name': name,
                    'quantity': quantity,
                    'current_price': current_price,
                    'holding_value': holding_value,
                    'holding_value_cny': holding_value_cny,
                    'currency': currency,
                    'platform': platform,
                    'exchange_rate': exchange_rate if currency.upper() == 'USD' else 1.0
                })
            else:
                print(f"无法获取 {symbol} 的价格")
        
        return holdings_data, total_value_cny
    
    def generate_report(self):
        """生成投资组合报告"""
        holdings_data, total_value = self.calculate_portfolio_value()
        
        if not holdings_data:
            return "无法获取任何股票价格数据"
        
        # 创建表格
        report_lines = []
        report_lines.append("=== 股票资产汇总报告 ===")
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        report_lines.append(f"{'股票代码':<10} {'名称':<12} {'数量':<8} {'当前价格':<10} {'持仓价值':<12} {'币种':<6} {'平台':<10}")
        report_lines.append("-" * 80)
        
        for holding in holdings_data:
            report_lines.append(
                f"{holding['symbol']:<10} "
                f"{holding['name']:<12} "
                f"{holding['quantity']:<8} "
                f"{holding['current_price']:<10.3f} "
                f"{holding['holding_value_cny']:<12.2f} "
                f"{holding['currency']:<6} "
                f"{holding['platform']:<10}"
            )
        
        report_lines.append("-" * 80)
        report_lines.append(f"总资产价值: ¥{total_value:.2f}")
        
        return "\n".join(report_lines)

def main():
    tracker = StockTracker()
    report = tracker.generate_report()
    print(report)
    
    # 保存报告到文件
    with open("latest_report.txt", "w", encoding="utf-8") as f:
        f.write(report)

if __name__ == "__main__":
    main()