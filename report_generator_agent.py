#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告生成智能体 - 生成标准化投资报告
"""

import json
import sys
from datetime import datetime

def generate_report(portfolio_data: dict, template: str, format: str) -> dict:
    """生成投资报告"""
    
    # 计算总资产
    total_value = 0
    holdings_table = []
    
    for holding in portfolio_data.get('holdings', []):
        code = holding['code']
        name = holding['name']
        quantity = holding['quantity']
        price = holding['price']
        currency = holding['currency']
        platform = holding['platform']
        
        if currency == 'CNY':
            value_cny = price * quantity
        else:  # USD
            # 使用汇率 1 USD = 6.8803 CNY
            exchange_rate = 6.8803
            value_cny = price * quantity * exchange_rate
            
        total_value += value_cny
        
        holdings_table.append({
            'code': code,
            'name': name,
            'quantity': quantity,
            'price': price,
            'value_cny': round(value_cny, 2),
            'currency': currency,
            'platform': platform
        })
    
    # 生成报告内容
    if format == 'markdown_with_tables':
        report_content = generate_markdown_report(
            portfolio_data['date'], 
            holdings_table, 
            total_value
        )
    else:
        report_content = f"Portfolio Report for {portfolio_data['date']}: Total Value = {total_value:.2f} CNY"
    
    return {
        'timestamp': datetime.now().isoformat(),
        'report_content': report_content,
        'total_value': round(total_value, 2),
        'holdings_count': len(holdings_table),
        'format': format,
        'status': 'success'
    }

def generate_markdown_report(date: str, holdings: list, total_value: float) -> str:
    """生成Markdown格式报告"""
    lines = []
    lines.append("# 📈 股票投资组合日报")
    lines.append("")
    lines.append(f"📊 报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 📅 今日持仓详情")
    lines.append("| 股票代码 | 股票名称 | 持仓数量 | 当前价格 | 持仓价值 | 币种 | 平台 |")
    lines.append("|----------|----------|----------|----------|----------|------|------|")
    
    for holding in holdings:
        lines.append(f"| {holding['code']} | {holding['name']} | {holding['quantity']:.1f} | {holding['price']:.3f} | {holding['value_cny']:.2f} | {holding['currency']} | {holding['platform']} |")
    
    lines.append("")
    lines.append(f"## 💰 总资产: {total_value:.2f} CNY")
    
    return "\n".join(lines)

def main():
    """主函数"""
    try:
        # 从stdin读取输入
        input_data = sys.stdin.read()
        task_data = json.loads(input_data)
        
        # 提取参数
        portfolio_data = task_data.get('portfolio_data', {})
        template = task_data.get('template', 'daily_investment_report')
        format_type = task_data.get('format', 'markdown_with_tables')
        
        # 执行报告生成
        result = generate_report(portfolio_data, template, format_type)
        
        # 输出结果
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        error_result = {
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'status': 'error'
        }
        print(json.dumps(error_result, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()