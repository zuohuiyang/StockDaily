#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级金融分析 - 纯Python实现（无外部依赖）
"""

import math
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

def calculate_returns(prices: List[float]) -> List[float]:
    """计算收益率序列"""
    if len(prices) < 2:
        return []
    returns = []
    for i in range(1, len(prices)):
        if prices[i-1] != 0:
            returns.append((prices[i] - prices[i-1]) / prices[i-1])
        else:
            returns.append(0.0)
    return returns

def calculate_volatility(returns: List[float]) -> float:
    """计算波动率（年化）"""
    if len(returns) < 2:
        return 0.0
    std_dev = statistics.stdev(returns) if len(returns) > 1 else 0.0
    # 年化波动率（假设252个交易日）
    annualized_vol = std_dev * math.sqrt(252)
    return annualized_vol

def calculate_sharpe_ratio(portfolio_returns: List[float], risk_free_rate: float = 0.02) -> float:
    """计算夏普比率"""
    if len(portfolio_returns) < 2:
        return 0.0
    
    avg_return = statistics.mean(portfolio_returns)
    volatility = calculate_volatility(portfolio_returns)
    
    if volatility == 0:
        return 0.0
    
    # 年化夏普比率
    annualized_return = (1 + avg_return) ** 252 - 1
    sharpe = (annualized_return - risk_free_rate) / volatility
    return sharpe

def calculate_max_drawdown(prices: List[float]) -> Tuple[float, int, int]:
    """计算最大回撤"""
    if len(prices) < 2:
        return 0.0, 0, 0
    
    peak = prices[0]
    max_dd = 0.0
    peak_idx = 0
    trough_idx = 0
    
    for i, price in enumerate(prices):
        if price > peak:
            peak = price
            peak_idx = i
        else:
            dd = (peak - price) / peak if peak != 0 else 0
            if dd > max_dd:
                max_dd = dd
                trough_idx = i
    
    return max_dd, peak_idx, trough_idx

def calculate_portfolio_metrics(holdings: List[Dict], historical_data: Dict = None) -> Dict:
    """计算投资组合综合指标"""
    
    # 计算当前总资产和配置
    total_value = 0
    asset_allocation = {'USD': 0, 'CNY': 0}
    sector_exposure = {}
    
    for holding in holdings:
        code = holding['code']
        quantity = holding['quantity']
        price = holding['price']
        currency = holding['currency']
        value_cny = holding.get('value_cny', 0)
        
        total_value += value_cny
        
        # 资产配置
        if currency == 'USD':
            asset_allocation['USD'] += value_cny
        else:
            asset_allocation['CNY'] += value_cny
        
        # 行业暴露（简化版）
        sector = classify_sector(code)
        sector_exposure[sector] = sector_exposure.get(sector, 0) + value_cny
    
    # 计算风险指标
    usd_ratio = asset_allocation['USD'] / total_value if total_value > 0 else 0
    concentration_risk = calculate_concentration_risk(sector_exposure, total_value)
    diversification_score = 1.0 - concentration_risk
    
    # 模拟历史数据进行高级分析（如果可用）
    sharpe_ratio = 0.0
    max_drawdown = 0.0
    
    if historical_data:
        # 这里可以添加基于历史数据的分析
        pass
    
    metrics = {
        'total_value': round(total_value, 2),
        'asset_allocation': {
            'USD': round(asset_allocation['USD'], 2),
            'CNY': round(asset_allocation['CNY'], 2),
            'usd_ratio': round(usd_ratio, 4)
        },
        'sector_exposure': {k: round(v, 2) for k, v in sector_exposure.items()},
        'risk_metrics': {
            'sharpe_ratio': round(sharpe_ratio, 4),
            'max_drawdown': round(max_drawdown, 4),
            'concentration_risk': round(concentration_risk, 4),
            'diversification_score': round(diversification_score, 4)
        }
    }
    
    return metrics

def classify_sector(stock_code: str) -> str:
    """根据股票代码分类行业（简化版）"""
    # ETF分类
    if stock_code in ['QQQ', 'SOXX', 'VOO']:
        return '科技'
    elif stock_code in ['SGOV']:
        return '债券'
    elif stock_code in ['511260', '511520']:
        return '国债'
    elif stock_code in ['518850']:
        return '商品'
    
    # A股分类（基于代码前缀）
    if stock_code.startswith('600'):
        if stock_code == '600036':
            return '金融'
        elif stock_code == '600941':
            return '通信'
        elif stock_code == '601088':
            return '能源'
    
    # 美股分类
    if stock_code in ['TSLA', 'NVDA']:
        return '科技'
    
    return '其他'

def calculate_concentration_risk(sector_exposure: Dict[str, float], total_value: float) -> float:
    """计算集中度风险（赫芬达尔指数）"""
    if total_value == 0:
        return 0.0
    
    hhi = 0.0
    for value in sector_exposure.values():
        weight = value / total_value
        hhi += weight ** 2
    
    # 转换为0-1范围的风险指标
    concentration_risk = hhi
    return min(concentration_risk, 1.0)

def generate_investment_recommendations(metrics: Dict) -> List[str]:
    """基于指标生成投资建议"""
    recommendations = []
    
    usd_ratio = metrics['asset_allocation']['usd_ratio']
    concentration_risk = metrics['risk_metrics']['concentration_risk']
    diversification_score = metrics['risk_metrics']['diversification_score']
    
    # 外汇风险建议
    if usd_ratio > 0.8:
        recommendations.append("外汇风险较高：美元资产占比超过80%，建议考虑增加人民币资产配置")
    elif usd_ratio < 0.2:
        recommendations.append("外汇风险较低：美元资产占比不足20%，可考虑适当增加美元资产以分散风险")
    
    # 集中度风险建议
    if concentration_risk > 0.6:
        recommendations.append("集中度风险较高：建议分散投资到更多行业或资产类别")
    elif concentration_risk < 0.3:
        recommendations.append("分散度良好：投资组合行业分布较为均衡")
    
    # 多样化建议
    if diversification_score < 0.5:
        recommendations.append("多样化程度有待提升：考虑增加不同类型的资产（如债券、商品等）")
    
    if not recommendations:
        recommendations.append("投资组合整体风险控制良好，维持当前配置策略")
    
    return recommendations

def main():
    """测试函数"""
    # 示例持仓数据
    test_holdings = [
        {'code': 'NVDA', 'name': '英伟达', 'quantity': 1.0, 'price': 179.650, 'currency': 'USD', 'value_cny': 1236.05},
        {'code': 'QQQ', 'name': '纳斯达克100ETF', 'quantity': 1.0, 'price': 606.400, 'currency': 'USD', 'value_cny': 4172.21},
        {'code': '518850', 'name': '华安黄金ETF', 'quantity': 1.0, 'price': 11.020, 'currency': 'CNY', 'value_cny': 11.02}
    ]
    
    metrics = calculate_portfolio_metrics(test_holdings)
    recommendations = generate_investment_recommendations(metrics)
    
    print("=== 高级金融分析结果 ===")
    print(f"总资产: {metrics['total_value']} CNY")
    print(f"美元资产占比: {metrics['asset_allocation']['usd_ratio']:.2%}")
    print(f"集中度风险: {metrics['risk_metrics']['concentration_risk']:.4f}")
    print(f"多样化评分: {metrics['risk_metrics']['diversification_score']:.4f}")
    print("\n=== 投资建议 ===")
    for rec in recommendations:
        print(f"• {rec}")

if __name__ == "__main__":
    main()