#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地Cron调度器 - 替代网关cron功能
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, time
import schedule
import time as time_module

class LocalCronScheduler:
    def __init__(self):
        self.jobs = []
        
    def add_daily_job(self, time_str, script_path, job_name):
        """添加每日定时任务"""
        hour, minute = map(int, time_str.split(':'))
        target_time = time(hour, minute)
        
        # 使用schedule库安排任务
        schedule.every().day.at(time_str).do(self.run_script, script_path, job_name)
        
        self.jobs.append({
            'name': job_name,
            'time': time_str,
            'script': script_path,
            'next_run': datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        })
        
        print(f"已添加每日任务: {job_name} - {time_str}")
        
    def run_script(self, script_path, job_name):
        """执行脚本"""
        try:
            path = Path(script_path)
            ext = path.suffix.lower()
            if ext == ".py":
                cmd = [sys.executable, script_path]
            elif ext == ".ps1":
                cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path]
            elif ext == ".sh":
                cmd = ["bash", script_path]
            else:
                cmd = [script_path]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 任务 '{job_name}' 执行成功")
                print(f"输出: {result.stdout[:200]}...")
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 任务 '{job_name}' 执行失败")
                print(f"错误: {result.stderr[:200]}...")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 任务 '{job_name}' 执行异常: {e}")
            
    def start_scheduler(self):
        """启动调度器"""
        print("本地Cron调度器已启动")
        print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"已配置任务数量: {len(self.jobs)}")
        
        while True:
            schedule.run_pending()
            time_module.sleep(60)  # 每分钟检查一次
            
    def list_jobs(self):
        """列出所有任务"""
        return self.jobs

def main():
    scheduler = LocalCronScheduler()
    
    # 添加投资组合报告生成任务（每天17:30）
    scheduler.add_daily_job("17:30", "scripts/run_daily.ps1", "daily_portfolio_report")
    
    # 列出所有任务
    jobs = scheduler.list_jobs()
    print(f"\n已配置的任务 ({len(jobs)}):")
    for job in jobs:
        print(f"  - {job['name']}: {job['time']} -> {job['script']}")
    
    # 如果有命令行参数，启动调度器
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        scheduler.start_scheduler()

if __name__ == "__main__":
    main()
