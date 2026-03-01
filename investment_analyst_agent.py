#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投资分析专用智能体 - 提供深入的投资组合分析
"""

import json
import sys
from datetime import datetime

def analyze_portfolio(portfolio_data: dict, analysis_depth: str = 'comprehensive') -> dict:
    """分析投资组合"""
    try:
        # 基础分析
        total_value = sum(holding.get('value_cny', 0) for holding in portfolio_data.get('holdings', []))
        
        # 按资产类别分类
        asset_allocation = {'USD': 0, 'CNY': 0}
        sector_exposure = {}
        
        for holding in portfolio_data.get('holdings', []):
            currency = holding.get('currency', 'CNY')
            value = holding.get('value_cny', 0)
            asset_allocation[currency] += value
            
            # 简单的行业分类（基于股票名称）
            name = holding.get('name', '')
            if 'ETF' in name:
                sector = 'ETF'
            elif '银行' in name or '神华' in name:
                sector = '金融/能源'
            elif '移动' in name:
                sector = '通信'
            elif '黄金' in name:
                sector = '商品'
            elif any(x in name for x in ['英伟达', '特斯拉', '半导体']):
                sector = '科技'
            else:
                sector = '其他'
                
            sector_exposure[sector] = sector_exposure.get(sector, 0) + value
        
        # 风险指标计算（简化版）
        usd_exposure = asset_allocation.get('USD', 0) / total_value if total_value > 0 else 0
        concentration_risk = max(sector_exposure.values()) / total_value if total_value > 0 else 0
        
        analysis_result = {
            'analysis_type': 'investment_portfolio',
            'timestamp': datetime.now().isoformat(),
            'total_value': total_value,
            'asset_allocation': asset_allocation,
            'sector_exposure': sector_exposure,
            'risk_metrics': {
                'usd_exposure_ratio': usd_exposure,
                'concentration_risk': concentration_risk,
                'diversification_score': 1 - concentration_risk
            },
            'recommendations': []
        }
        
        # 生成建议
        if usd_exposure > 0.7:
            analysis_result['recommendations'].append('美元资产占比过高，考虑增加人民币资产配置以分散汇率风险')
        if concentration_risk > 0.4:
            analysis_result['recommendations'].append('投资集中度较高，建议进一步分散投资')
            
        return {
            'success': True,
            'data': analysis_result,
            'execution_time': 0.015  # 模拟执行时间
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'execution_time': 0
        }

def main():
    """主函数"""
    try:
        # 从stdin读取输入
        input_data = json.load(sys.stdin)
        task = input_data.get('task')
        
        if task == 'analyze_portfolio':
            result = analyze_portfolio(
                input_data.get('portfolio_data', {}),
                input_data.get('analysis_depth', 'comprehensive')
            )
        else:
            result = {
                'success': False,
                'error': f'Unknown task: {task}',
                'execution_time': 0
            }
            
        # 输出结果到stdout
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        error_result = {
            'success': False,
            'error': str(e),
            'execution_time': 0
        }
        print(json.dumps(error_result, ensure_ascii=False))

if __name__ == "__main__":
    main()