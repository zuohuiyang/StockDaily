#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能监控智能体 - 监控系统性能指标
"""

import json
import sys
import time
from datetime import datetime

def monitor_performance(portfolio_data: dict, metrics: list) -> dict:
    """监控性能指标"""
    start_time = time.time()
    
    # 模拟性能监控
    performance_metrics = {
        'response_time': 0.045,  # 秒
        'accuracy': 0.998,       # 准确率
        'resource_usage': {
            'cpu_percent': 12.5,
            'memory_mb': 256,
            'disk_io': 0.8
        },
        'portfolio_size': len(portfolio_data.get('holdings', [])),
        'data_freshness': 'real-time'
    }
    
    # 只返回请求的指标
    if metrics:
        filtered_metrics = {}
        for metric in metrics:
            if metric in performance_metrics:
                filtered_metrics[metric] = performance_metrics[metric]
            elif metric == 'response_time':
                filtered_metrics['response_time'] = performance_metrics['response_time']
            elif metric == 'accuracy':
                filtered_metrics['accuracy'] = performance_metrics['accuracy']
            elif metric == 'resource_usage':
                filtered_metrics['resource_usage'] = performance_metrics['resource_usage']
    else:
        filtered_metrics = performance_metrics
    
    execution_time = time.time() - start_time
    
    return {
        'timestamp': datetime.now().isoformat(),
        'metrics': filtered_metrics,
        'execution_time': execution_time,
        'status': 'success'
    }

def main():
    """主函数"""
    try:
        # 从stdin读取输入
        input_data = sys.stdin.read()
        task_data = json.loads(input_data)
        
        # 提取参数
        portfolio_data = task_data.get('portfolio_data', {})
        metrics = task_data.get('metrics', [])
        
        # 执行性能监控
        result = monitor_performance(portfolio_data, metrics)
        
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