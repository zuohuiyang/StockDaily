#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级金融分析模块 - 计算风险指标、资产配置优化等
"""

import sqlite3
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class AdvancedFinancialAnalyzer:
    def __init__(self, db_path: str = 'portfolio.db'):
        self.db_path = db_path
        
    def calculate_sharpe_ratio(self, portfolio_data: List[Dict]) -> float:
        """计算夏普比率"""
        # 简化版本：基于历史数据计算
        if len(portfolio_data) < 2:
            return 0.0
            
        returns = []
        for i in range(1, len(portfolio_data)):
            prev_value = portfolio_data[i-1]['total_value']
            curr_value = portfolio_data[i]['total_value']
            if prev_value > 0:
                returns.append((curr_value - prev_value) / prev_value)
        
        if not returns:
            return 0.0
            
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        # 无风险利率假设为2%
        risk_free_rate = 0.02 / 252  # 日化
        
        if std_return == 0:
            return 0.0
            
        sharpe_ratio = (avg_return - risk_free_rate) / std_return * np.sqrt(252)
        return sharpe_ratio
    
    def calculate_max_drawdown(self, portfolio_data: List[Dict]) -> Tuple[float, str, str]:
        """计算最大回撤"""
        if len(portfolio_data) < 2:
            return 0.0, "", ""
            
        values = [data['total_value'] for data in portfolio_data]
        dates = [data['date'] for data in portfolio_data]
        
        peak = values[0]
        max_drawdown = 0
        drawdown_start = dates[0]
        drawdown_end = dates[0]
        peak_date = dates[0]
        
        for i, (value, date) in enumerate(zip(values, dates)):
            if value > peak:
                peak = value
                peak_date = date
                
            drawdown = (peak - value) / peak if peak > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                drawdown_start = peak_date
                drawdown_end = date
                
        return max_drawdown, drawdown_start, drawdown_end
    
    def analyze_asset_allocation(self, current_holdings: List[Dict]) -> Dict:
        """分析资产配置"""
        allocation = {
            'by_currency': {'USD': 0, 'CNY': 0},
            'by_sector': {},
            'by_asset_type': {'ETF': 0, 'Stock': 0, 'Bond': 0}
        }
        
        total_value = 0
        exchange_rate = 6.8803  # USD to CNY
        
        for holding in current_holdings:
            code = holding['code']
            quantity = holding['quantity']
            price = holding['price']
            currency = holding['currency']
            
            if currency == 'CNY':
                value_cny = price * quantity
            else:
                value_cny = price * quantity * exchange_rate
                
            total_value += value_cny
            allocation['by_currency'][currency] += value_cny
            
            # 分类资产类型和行业
            asset_type, sector = self._classify_asset(code, holding['name'])
            if asset_type in allocation['by_asset_type']:
                allocation['by_asset_type'][asset_type] += value_cny
            else:
                allocation['by_asset_type']['Other'] = allocation['by_asset_type'].get('Other', 0) + value_cny
                
            allocation['by_sector'][sector] = allocation['by_sector'].get(sector, 0) + value_cny
        
        # 转换为百分比
        if total_value > 0:
            for key in allocation['by_currency']:
                allocation['by_currency'][key] = round(allocation['by_currency'][key] / total_value * 100, 2)
                
            for key in allocation['by_asset_type']:
                allocation['by_asset_type'][key] = round(allocation['by_asset_type'][key] / total_value * 100, 2)
                
            for key in allocation['by_sector']:
                allocation['by_sector'][key] = round(allocation['by_sector'][key] / total_value * 100, 2)
        
        allocation['total_value'] = total_value
        return allocation
    
    def _classify_asset(self, code: str, name: str) -> Tuple[str, str]:
        """分类资产类型和行业"""
        # ETF识别
        etf_keywords = ['ETF', 'etf', '指数', '跟踪']
        if any(keyword in name for keyword in etf_keywords):
            asset_type = 'ETF'
        elif code.isdigit():  # A股代码
            asset_type = 'Stock'
        else:  # 美股代码
            asset_type = 'Stock'
            
        # 行业分类
        if '黄金' in name or 'gold' in name.lower():
            sector = '贵金属'
        elif '国债' in name or 'bond' in name.lower() or 'SGOV' in code:
            sector = '债券'
        elif '半导体' in name or 'SOXX' in code:
            sector = '科技'
        elif '纳斯达克' in name or 'QQQ' in code:
            sector = '科技'
        elif '标普' in name or 'VOO' in code:
            sector = '大盘指数'
        elif '英伟达' in name or 'NVDA' in code:
            sector = '科技'
        elif '特斯拉' in name or 'TSLA' in code:
            sector = '新能源/汽车'
        elif '招商银行' in name:
            sector = '金融'
        elif '中国移动' in name:
            sector = '通信'
        elif '中国神华' in name:
            sector = '能源'
        else:
            sector = '其他'
            
        return asset_type, sector
    
    def get_historical_portfolio_data(self, days: int = 30) -> List[Dict]:
        """获取历史投资组合数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取日期范围
        cursor.execute('SELECT DISTINCT date FROM stock_prices ORDER BY date DESC LIMIT ?', (days,))
        dates = [row[0] for row in cursor.fetchall()]
        
        historical_data = []
        
        for date in sorted(dates):
            # 获取该日期的持仓价值
            cursor.execute('SELECT code, name, quantity, currency, platform FROM holdings')
            holdings = cursor.fetchall()
            
            total_value = 0
            exchange_rate = 6.8803
            
            for code, name, quantity, currency, platform in holdings:
                cursor.execute('SELECT price FROM stock_prices WHERE code = ? AND date = ?', (code, date))
                price_result = cursor.fetchone()
                price = price_result[0] if price_result else 0
                
                if currency == 'CNY':
                    value_cny = price * quantity
                else:
                    value_cny = price * quantity * exchange_rate
                    
                total_value += value_cny
            
            historical_data.append({
                'date': date,
                'total_value': total_value
            })
        
        conn.close()
        return historical_data
    
    def generate_investment_recommendations(self, allocation: Dict) -> List[str]:
        """生成投资建议"""
        recommendations = []
        
        # 货币配置建议
        usd_pct = allocation['by_currency'].get('USD', 0)
        cny_pct = allocation['by_currency'].get('CNY', 0)
        
        if usd_pct > 80:
            recommendations.append("⚠️ 美元资产占比过高（{}%），建议适当增加人民币资产以分散汇率风险".format(usd_pct))
        elif cny_pct > 80:
            recommendations.append("⚠️ 人民币资产占比过高（{}%），建议适当增加美元资产以分散汇率风险".format(cny_pct))
            
        # 行业集中度建议
        tech_pct = allocation['by_sector'].get('科技', 0)
        if tech_pct > 60:
            recommendations.append("⚠️ 科技股集中度过高（{}%），建议分散到其他行业".format(tech_pct))
            
        # 资产类型建议
        etf_pct = allocation['by_asset_type'].get('ETF', 0)
        stock_pct = allocation['by_asset_type'].get('Stock', 0)
        
        if etf_pct < 30 and stock_pct > 70:
            recommendations.append("💡 股票个股占比较高（{}%），考虑增加ETF配置以降低个股风险".format(stock_pct))
        elif etf_pct > 70:
            recommendations.append("💡 ETF配置比例较高（{}%），如寻求更高收益可适当增加优质个股".format(etf_pct))
            
        if not recommendations:
            recommendations.append("✅ 资产配置相对均衡，风险分散良好")
            
        return recommendations

def main():
    """测试函数"""
    analyzer = AdvancedFinancialAnalyzer()
    
    # 获取当前持仓
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT date FROM stock_prices ORDER BY date DESC LIMIT 1')
    latest_date = cursor.fetchone()[0]
    
    cursor.execute('SELECT code, name, quantity, currency, platform FROM holdings')
    holdings = cursor.fetchall()
    
    current_holdings = []
    for code, name, quantity, currency, platform in holdings:
        cursor.execute('SELECT price FROM stock_prices WHERE code = ? AND date = ?', (code, latest_date))
        price_result = cursor.fetchone()
        price = price_result[0] if price_result else 0
        
        current_holdings.append({
            'code': code,
            'name': name,
            'quantity': quantity,
            'price': price,
            'currency': currency,
            'platform': platform
        })
    
    conn.close()
    
    # 分析资产配置
    allocation = analyzer.analyze_asset_allocation(current_holdings)
    print("资产配置分析:")
    print(json.dumps(allocation, indent=2, ensure_ascii=False))
    
    # 生成建议
    recommendations = analyzer.generate_investment_recommendations(allocation)
    print("\n投资建议:")
    for rec in recommendations:
        print(f"- {rec}")
    
    # 获取历史数据并计算风险指标
    historical_data = analyzer.get_historical_portfolio_data(30)
    if len(historical_data) >= 2:
        sharpe = analyzer.calculate_sharpe_ratio(historical_data)
        max_dd, dd_start, dd_end = analyzer.calculate_max_drawdown(historical_data)
        
        print(f"\n风险指标:")
        print(f"- 夏普比率: {sharpe:.2f}")
        print(f"- 最大回撤: {max_dd:.2%} ({dd_start} 到 {dd_end})")

if __name__ == "__main__":
    import json
    main()