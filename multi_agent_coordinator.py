#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多智能体协调器 - 管理投资分析、性能监控和报告生成智能体
"""

import json
import subprocess
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

class MultiAgentCoordinator:
    def __init__(self):
        self.agents = {
            'investment_analyst': 'investment_analyst_agent.py',
            'performance_monitor': 'performance_monitor_agent.py', 
            'report_generator': 'report_generator_agent.py'
        }
        self.results = {}
        
    def execute_agent(self, agent_name: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行指定智能体并返回结果"""
        try:
            # 准备输入数据
            input_json = json.dumps(task_data)
            
            # 获取脚本路径
            script_path = self.agents[agent_name]
            
            # 执行智能体脚本
            result = subprocess.run([
                sys.executable, script_path
            ], input=input_json, text=True, capture_output=True, timeout=30)
            
            if result.returncode == 0:
                try:
                    output_data = json.loads(result.stdout)
                    return {
                        'success': True,
                        'data': output_data,
                        'execution_time': None
                    }
                except json.JSONDecodeError:
                    return {
                        'success': False,
                        'error': f"Invalid JSON output: {result.stdout[:200]}",
                        'execution_time': None
                    }
            else:
                return {
                    'success': False,
                    'error': result.stderr,
                    'execution_time': None
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'execution_time': None
            }
    
    def parallel_execute(self, tasks: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """并行执行多个智能体任务"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            # 提交所有任务
            future_to_agent = {
                executor.submit(self.execute_agent, agent_name, task_data): agent_name
                for agent_name, task_data in tasks.items()
            }
            
            # 收集结果
            for future in as_completed(future_to_agent):
                agent_name = future_to_agent[future]
                try:
                    results[agent_name] = future.result()
                except Exception as e:
                    results[agent_name] = {
                        'success': False,
                        'error': str(e),
                        'execution_time': None
                    }
        
        return results
    
    def generate_comprehensive_report(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成综合报告 - 协调所有智能体"""
        start_time = datetime.now()
        
        # 定义各智能体的任务
        tasks = {
            'investment_analyst': {
                'task': 'analyze_portfolio',
                'portfolio_data': portfolio_data,
                'analysis_depth': 'comprehensive'
            },
            'performance_monitor': {
                'task': 'monitor_performance',
                'portfolio_data': portfolio_data,
                'metrics': ['response_time', 'accuracy', 'resource_usage']
            },
            'report_generator': {
                'task': 'generate_report',
                'portfolio_data': portfolio_data,
                'template': 'daily_investment_report',
                'format': 'markdown_with_tables'
            }
        }
        
        # 并行执行所有智能体
        results = self.parallel_execute(tasks)
        
        # 汇总结果
        comprehensive_result = {
            'timestamp': datetime.now().isoformat(),
            'execution_time_total': (datetime.now() - start_time).total_seconds(),
            'agents_results': results,
            'success': all(result.get('success', False) for result in results.values())
        }
        
        return comprehensive_result

def main():
    """主函数 - 用于测试"""
    import sqlite3
    
    # 获取投资组合数据
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
    
    # 执行多智能体协调
    coordinator = MultiAgentCoordinator()
    result = coordinator.generate_comprehensive_report(portfolio_data)
    
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()