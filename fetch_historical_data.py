#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史股票数据获取器 - 用于修复缺失的历史数据
"""
import sqlite3
import json
import requests
from datetime import datetime

def get_yahoo_historical_price(symbol, date):
    """从Yahoo Finance获取历史价格"""
    try:
        # Yahoo Finance API endpoint
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            'period1': int(datetime.strptime(date, '%Y-%m-%d').timestamp()),
            'period2': int(datetime.strptime(date, '%Y-%m-%d').timestamp()) + 86400,
            'interval': '1d',
            'events': 'history'
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'chart' in data and 'result' in data['chart']:
                result = data['chart']['result']
                if result and len(result) > 0:
                    quotes = result[0]['indicators']['quote'][0]
                    if 'close' in quotes and quotes['close']:
                        return quotes['close'][0]
    except Exception as e:
        print(f"Yahoo Finance {symbol} 获取失败: {e}")
    return None

def get_a_stock_historical_price(code, date):
    """获取A股历史价格"""
    try:
        # 使用腾讯财经历史数据接口
        market = 'sz' if code.startswith(('0', '3')) else 'sh'
        url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        params = {
            '_var': 'kline_dayqfq',
            'param': f'{market}{code},day,{date},{date},1,qfq',
            'r': '0.123456789'
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            # 解析返回的JSONP格式
            text = response.text
            if 'kline_dayqfq=' in text:
                json_str = text.split('kline_dayqfq=')[1]
                json_str = json_str.strip()
                if json_str.endswith(';'):
                    json_str = json_str[:-1]
                data = json.loads(json_str)
                if 'data' in data and market+code in data['data']:
                    klines = data['data'][market+code]['day']
                    if klines and len(klines) > 0:
                        # kline格式: [日期, 开盘, 收盘, 最高, 最低, 成交量]
                        return float(klines[0][2])  # 收盘价
    except Exception as e:
        print(f"A股 {code} 历史数据获取失败: {e}")
    return None

def fix_missing_historical_data(target_date):
    """修复指定日期的缺失历史数据"""
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    
    # 获取所有持仓
    cursor.execute("SELECT code, currency FROM holdings")
    holdings = cursor.fetchall()
    
    # 检查哪些股票在目标日期缺少数据
    existing_codes = set()
    cursor.execute("SELECT code FROM stock_prices WHERE date = ?", (target_date,))
    for row in cursor.fetchall():
        existing_codes.add(row[0])
    
    missing_stocks = []
    for code, currency in holdings:
        if code not in existing_codes:
            missing_stocks.append((code, currency))
    
    print(f"发现 {len(missing_stocks)} 只股票在 {target_date} 缺失数据")
    
    # 尝试获取缺失数据
    for code, currency in missing_stocks:
        price = None
        if currency == 'CNY':
            price = get_a_stock_historical_price(code, target_date)
        elif currency == 'USD':
            # 对于美股，可能需要添加.US后缀
            yahoo_symbol = code
            price = get_yahoo_historical_price(yahoo_symbol, target_date)
            if price is None:
                # 尝试其他后缀
                price = get_yahoo_historical_price(code + '.US', target_date)
        
        if price is not None:
            cursor.execute("""
                INSERT INTO stock_prices (code, price, currency, date, source)
                VALUES (?, ?, ?, ?, ?)
            """, (code, price, currency, target_date, 'historical_fix'))
            print(f"✅ {code} 历史价格修复: {price}")
        else:
            print(f"⚠️  {code} 历史价格获取失败")
    
    conn.commit()
    conn.close()
    return len(missing_stocks)

if __name__ == "__main__":
    # 修复2026-02-27的数据
    fixed_count = fix_missing_historical_data('2026-02-27')
    print(f"修复完成，共处理 {fixed_count} 只股票")
