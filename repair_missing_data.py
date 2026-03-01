#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复缺失的股票价格数据 - 使用线性插值
"""

import sqlite3
from datetime import datetime

def get_price_for_date(conn, code, date):
    """获取指定日期的价格"""
    cursor = conn.cursor()
    cursor.execute("SELECT price FROM stock_prices WHERE code = ? AND date = ?", (code, date))
    result = cursor.fetchone()
    return result[0] if result else None

def repair_missing_data():
    """修复2026-02-27的缺失数据"""
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    
    # 获取所有持仓股票
    cursor.execute("SELECT code FROM holdings")
    all_codes = [row[0] for row in cursor.fetchall()]
    
    # 检查2026-02-27哪些股票缺失
    cursor.execute("SELECT code FROM stock_prices WHERE date = '2026-02-27'")
    existing_codes = [row[0] for row in cursor.fetchall()]
    
    missing_codes = [code for code in all_codes if code not in existing_codes]
    print(f"发现 {len(missing_codes)} 只股票在 2026-02-27 缺失数据: {missing_codes}")
    
    repaired_count = 0
    
    for code in missing_codes:
        # 获取2026-02-26和2026-02-28的价格
        price_26 = get_price_for_date(conn, code, '2026-02-26')
        price_28 = get_price_for_date(conn, code, '2026-02-28')
        
        if price_26 is not None and price_28 is not None:
            # 线性插值：2026-02-27的价格 = (price_26 + price_28) / 2
            interpolated_price = (price_26 + price_28) / 2
            
            # 获取币种
            cursor.execute("SELECT currency FROM holdings WHERE code = ?", (code,))
            currency_result = cursor.fetchone()
            currency = currency_result[0] if currency_result else 'CNY'
            
            # 插入修复的数据
            cursor.execute("""
                INSERT INTO stock_prices (code, price, currency, date, source)
                VALUES (?, ?, ?, ?, ?)
            """, (code, interpolated_price, currency, '2026-02-27', 'interpolated'))
            
            print(f"✅ {code} 修复成功: {interpolated_price:.3f}")
            repaired_count += 1
        else:
            print(f"⚠️  {code} 无法修复 - 缺少相邻日期数据")
    
    conn.commit()
    conn.close()
    
    print(f"修复完成，共修复 {repaired_count} 只股票")
    return repaired_count

if __name__ == "__main__":
    repair_missing_data()