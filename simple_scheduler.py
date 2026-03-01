#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的本地调度器 - 不依赖外部库
"""

import time
import subprocess
import sys
from datetime import datetime, timedelta

def schedule_daily_task(hour, minute, script_path):
    """调度每日任务"""
    while True:
        now = datetime.now()
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # 如果今天的时间已过，设置为明天
        if now > target_time:
            target_time += timedelta(days=1)
            
        # 计算等待时间
        wait_seconds = (target_time - now).total_seconds()
        
        print(f"下次执行时间: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"等待 {wait_seconds:.0f} 秒...")
        
        # 等待到目标时间
        time.sleep(wait_seconds)
        
        # 执行任务
        try:
            print(f"执行任务: {script_path}")
            result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
            if result.returncode == 0:
                print("任务执行成功")
            else:
                print(f"任务执行失败: {result.stderr}")
        except Exception as e:
            print(f"执行任务时出错: {e}")

def main():
    """主函数 - 调度每日5:30的投资报告生成"""
    if len(sys.argv) != 2:
        print("用法: python simple_scheduler.py <script_path>")
        sys.exit(1)
        
    script_path = sys.argv[1]
    schedule_daily_task(17, 30, script_path)  # 17:30 = 5:30 PM

if __name__ == "__main__":
    main()