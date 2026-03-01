#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票资产追踪系统 - SQLite版本
支持多平台、多币种的股票持仓管理
"""

import sqlite3
import json
import os
from datetime import datetime, date
import requests
import time

class StockTracker:
    def __init__(self, db_path="stock_tracker.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 持仓表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                quantity REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'CNY',
                platform TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 股票价格历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'CNY',
                date DATE NOT NULL,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(code, date, currency)
            )
        ''')
        
        # 汇率历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exchange_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_currency TEXT NOT NULL,
                to_currency TEXT NOT NULL,
                rate REAL NOT NULL,
                date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(from_currency, to_currency, date)
            )
        ''')
        
        # 投资组合价值历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_value_cny REAL NOT NULL,
                total_value_usd REAL,
                date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_holding(self, code, name, quantity, currency='CNY', platform=None):
        """添加持仓记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO holdings (code, name, quantity, currency, platform, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (code, name, quantity, currency, platform))
        
        conn.commit()
        conn.close()
        print(f"✅ 已添加持仓: {code} {name} {quantity}股 ({currency})")
    
    def get_current_price(self, code, currency='CNY'):
        """获取当前股票价格（简化版本，实际使用时可集成更多数据源）"""
        today = date.today().isoformat()
        
        # 先检查数据库中是否有今天的价格
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT price FROM stock_prices 
            WHERE code = ? AND date = ? AND currency = ?
        ''', (code, today, currency))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        
        # 如果没有缓存，返回None（需要手动输入或从API获取）
        return None
    
    def save_price(self, code, price, currency='CNY', date_str=None):
        """保存股票价格到数据库"""
        if date_str is None:
            date_str = date.today().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO stock_prices (code, price, currency, date, source)
            VALUES (?, ?, ?, ?, 'manual')
        ''', (code, price, currency, date_str))
        
        conn.commit()
        conn.close()
    
    def save_exchange_rate(self, from_currency, to_currency, rate, date_str=None):
        """保存汇率到数据库"""
        if date_str is None:
            date_str = date.today().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO exchange_rates (from_currency, to_currency, rate, date)
            VALUES (?, ?, ?, ?)
        ''', (from_currency, to_currency, rate, date_str))
        
        conn.commit()
        conn.close()
    
    def get_exchange_rate(self, from_currency, to_currency, date_str=None):
        """获取汇率"""
        if date_str is None:
            date_str = date.today().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT rate FROM exchange_rates 
            WHERE from_currency = ? AND to_currency = ? AND date = ?
        ''', (from_currency, to_currency, date_str))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def calculate_portfolio_value(self):
        """计算当前投资组合总价值"""
        today = date.today().isoformat()
        total_cny = 0.0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取所有持仓
        cursor.execute('SELECT code, name, quantity, currency FROM holdings')
        holdings = cursor.fetchall()
        
        print(f"📊 查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)
        print(f"📈 股票投资组合汇总 (SQLite版本)")
        print("=" * 100)
        print(f"{'股票代码':<12} {'股票名称':<15} {'持仓数量':<12} {'当前价格':<12} {'持仓价值':<12} {'币种':<8}")
        print("-" * 100)
        
        for code, name, quantity, currency in holdings:
            # 获取价格
            price = self.get_current_price(code, currency)
            if price is None:
                # 需要手动输入价格
                print(f"⚠️  {code} 未找到今日价格，请手动输入:")
                try:
                    price_input = input(f"请输入 {code} {name} 的当前价格 ({currency}): ")
                    price = float(price_input)
                    self.save_price(code, price, currency)
                except (ValueError, KeyboardInterrupt):
                    print(f"❌ 跳过 {code}")
                    continue
            
            # 计算价值
            value = price * quantity
            
            # 转换为人民币（如果需要）
            if currency == 'USD':
                usd_to_cny = self.get_exchange_rate('USD', 'CNY')
                if usd_to_cny is None:
                    print(f"⚠️  未找到 USD/CNY 汇率，请手动输入:")
                    try:
                        rate_input = input("请输入当前美元兑人民币汇率: ")
                        usd_to_cny = float(rate_input)
                        self.save_exchange_rate('USD', 'CNY', usd_to_cny)
                    except (ValueError, KeyboardInterrupt):
                        print("❌ 使用默认汇率 7.2")
                        usd_to_cny = 7.2
                        self.save_exchange_rate('USD', 'CNY', usd_to_cny)
                value_cny = value * usd_to_cny
                print(f"{code:<12} {name:<15} {quantity:<12} {price:<12.3f} {value_cny:<12.2f} {currency:<8} (≈{value:.2f} USD)")
                total_cny += value_cny
            else:
                print(f"{code:<12} {name:<15} {quantity:<12} {price:<12.3f} {value:<12.2f} {currency:<8}")
                total_cny += value
        
        print("-" * 100)
        print(f"{'总计':<52} {total_cny:<12.2f} CNY")
        print("=" * 100)
        
        # 保存投资组合价值历史
        cursor.execute('''
            INSERT OR REPLACE INTO portfolio_values (total_value_cny, date)
            VALUES (?, ?)
        ''', (total_cny, today))
        
        conn.commit()
        conn.close()
        
        return total_cny
    
    def get_portfolio_history(self, days=30):
        """获取投资组合历史价值"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT date, total_value_cny 
            FROM portfolio_values 
            ORDER BY date DESC 
            LIMIT ?
        ''', (days,))
        
        history = cursor.fetchall()
        conn.close()
        
        return history

def main():
    tracker = StockTracker()
    
    # 初始化示例数据（518850 华安黄金ETF）
    tracker.add_holding("518850", "华安黄金ETF", 1, "CNY", "银河证券")
    
    # 计算并显示投资组合价值
    tracker.calculate_portfolio_value()

if __name__ == "__main__":
    main()