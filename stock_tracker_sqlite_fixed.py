#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票资产追踪系统 (SQLite版本)
支持多平台、多币种股票持仓管理
"""

import sqlite3
import json
import os
import requests
from datetime import datetime, date
import sys

# 数据库文件路径
DB_PATH = "stock_portfolio.db"

def init_database():
    """初始化数据库表结构"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 持仓信息表
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 投资组合价值历史表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio_values (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_value_cny REAL NOT NULL,
            total_value_usd REAL NOT NULL,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_holdings_code ON holdings(code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_prices_code_date ON stock_prices(code, date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_rates_date ON exchange_rates(date)')
    
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")

def add_holding(code, name, quantity, currency='CNY', platform=None):
    """添加或更新持仓"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查是否已存在
    cursor.execute('SELECT id, quantity FROM holdings WHERE code = ?', (code,))
    existing = cursor.fetchone()
    
    if existing:
        # 更新现有持仓
        new_quantity = existing[1] + quantity
        cursor.execute('''
            UPDATE holdings 
            SET quantity = ?, name = ?, currency = ?, platform = ?, updated_at = CURRENT_TIMESTAMP
            WHERE code = ?
        ''', (new_quantity, name, currency, platform, code))
        print("🔄 已更新持仓: {} {} {}股 ({})".format(code, name, new_quantity, currency))
    else:
        # 添加新持仓
        cursor.execute('''
            INSERT INTO holdings (code, name, quantity, currency, platform)
            VALUES (?, ?, ?, ?, ?)
        ''', (code, name, quantity, currency, platform))
        print("✅ 已添加持仓: {} {} {}股 ({})".format(code, name, quantity, currency))
    
    conn.commit()
    conn.close()

def get_current_price(code, currency='CNY'):
    """获取当前股票价格（简化版本，返回None表示需要手动输入）"""
    # 这里可以集成实际的API调用
    # 目前先返回None，让用户手动输入
    return None

def save_price(code, price, currency='CNY', date_str=None):
    """保存股票价格到数据库"""
    if date_str is None:
        date_str = date.today().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查今天是否已有价格
    cursor.execute('SELECT id FROM stock_prices WHERE code = ? AND date = ?', (code, date_str))
    existing = cursor.fetchone()
    
    if existing:
        # 更新价格
        cursor.execute('''
            UPDATE stock_prices SET price = ?, currency = ? WHERE code = ? AND date = ?
        ''', (price, currency, code, date_str))
    else:
        # 插入新价格
        cursor.execute('''
            INSERT INTO stock_prices (code, price, currency, date, source)
            VALUES (?, ?, ?, ?, ?)
        ''', (code, price, currency, date_str, 'manual'))
    
    conn.commit()
    conn.close()

def get_latest_price(code, date_str=None):
    """获取最新价格"""
    if date_str is None:
        date_str = date.today().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT price, currency FROM stock_prices 
        WHERE code = ? AND date = ? 
        ORDER BY created_at DESC LIMIT 1
    ''', (code, date_str))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0], result[1]
    return None, None

def calculate_portfolio():
    """计算投资组合价值"""
    today = date.today().isoformat()
    total_value_cny = 0.0
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取所有持仓
    cursor.execute('SELECT code, name, quantity, currency FROM holdings')
    holdings = cursor.fetchall()
    conn.close()
    
    if not holdings:
        print("📭 暂无持仓记录")
        return
    
    # 打印表头
    header = "{:<12} {:<15} {:<12} {:<12} {:<12} {:<8}".format(
        "股票代码", "股票名称", "持仓数量", "当前价格", "持仓价值", "币种"
    )
    separator = "-" * len(header)
    
    print("\n📊 查询时间: {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    print("=" * len(header))
    print("📈 股票投资组合汇总 (SQLite版本)")
    print("=" * len(header))
    print(header)
    print("-" * len(header))
    
    for code, name, quantity, currency in holdings:
        # 获取最新价格
        price, price_currency = get_latest_price(code, today)
        
        if price is None:
            # 需要手动输入价格
            print("⚠️  {} 未找到今日价格，请手动输入:".format(code))
            try:
                price_input = input("请输入 {} {} 的当前价格 ({}): ".format(code, name, currency))
                price = float(price_input)
                # 保存价格
                save_price(code, price, currency, today)
                price_currency = currency
            except (ValueError, KeyboardInterrupt):
                print("❌ 价格输入无效，跳过此股票")
                continue
        
        # 计算持仓价值
        holding_value = quantity * price
        
        # 如果是美元，需要转换为人民币（这里简化处理，假设汇率为7.2）
        if currency.upper() == 'USD':
            exchange_rate = 7.2  # 简化汇率
            holding_value_cny = holding_value * exchange_rate
            total_value_cny += holding_value_cny
            value_display = "{:.2f} ({:.2f} CNY)".format(holding_value, holding_value_cny)
        else:
            total_value_cny += holding_value
            value_display = "{:.2f}".format(holding_value)
        
        # 打印行
        row = "{:<12} {:<15} {:<12.2f} {:<12.3f} {:<12} {:<8}".format(
            code, name, quantity, price, value_display, currency
        )
        print(row)
    
    print("-" * len(header))
    print("总计                                                 {:.2f} CNY".format(total_value_cny))
    print("=" * len(header))

def main():
    """主函数"""
    # 初始化数据库
    init_database()
    
    # 添加示例持仓（518850 华安黄金ETF）
    add_holding("518850", "华安黄金ETF", 1, "CNY", "银河证券")
    
    # 计算投资组合
    calculate_portfolio()

if __name__ == "__main__":
    main()