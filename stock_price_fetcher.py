#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票价格获取器 - 支持多种数据源
"""
import json
import requests
import sqlite3
from datetime import datetime

def get_a_stock_price(code):
    """获取A股价格 - 使用腾讯财经接口"""
    try:
        url = f"http://qt.gtimg.cn/q=sz{code}" if code.startswith(('0', '3')) else f"http://qt.gtimg.cn/q=sh{code}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.text
            # 解析腾讯财经返回的数据
            if 'v_' in data:
                parts = data.split('~')
                if len(parts) > 4:
                    price = float(parts[3])
                    return price
    except Exception as e:
        print(f"A股 {code} 获取失败: {e}")
    return None

def get_us_stock_price_alpha_vantage(symbol, api_key):
    """使用Alpha Vantage获取美股价格"""
    try:
        url = f"https://www.alphavantage.co/query"
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': symbol,
            'apikey': api_key
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'Global Quote' in data:
                quote = data['Global Quote']
                if '05. price' in quote:
                    return float(quote['05. price'])
    except Exception as e:
        print(f"美股 {symbol} Alpha Vantage获取失败: {e}")
    return None

def get_exchange_rate():
    """获取美元兑人民币汇率"""
    try:
        # 使用中国银行外汇牌价
        url = "https://www.boc.cn/sourcedb/whpj/"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            # 简化处理，这里用固定汇率作为备选
            return 6.8500
    except Exception as e:
        print(f"汇率获取失败: {e}")
    
    # 备用汇率
    return 6.8500

def update_stock_prices():
    """更新所有持仓股票的价格"""
    # 读取API配置
    try:
        with open('api_config.json', 'r') as f:
            api_config = json.load(f)
        alpha_vantage_key = api_config.get('alpha_vantage_api_key')
    except:
        alpha_vantage_key = None
    
    # 连接数据库
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    
    # 获取所有持仓
    cursor.execute("SELECT code, currency FROM holdings")
    holdings = cursor.fetchall()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    for code, currency in holdings:
        price = None
        if currency == 'CNY':
            price = get_a_stock_price(code)
        elif currency == 'USD' and alpha_vantage_key:
            price = get_us_stock_price_alpha_vantage(code, alpha_vantage_key)
        
        if price is not None:
            # 更新价格到数据库
            cursor.execute("""
                INSERT OR REPLACE INTO stock_prices (code, price, currency, date, source)
                VALUES (?, ?, ?, ?, ?)
            """, (code, price, currency, today, 'auto'))
            print(f"✅ {code} 价格更新: {price}")
        else:
            print(f"⚠️  {code} 价格获取失败")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_stock_prices()