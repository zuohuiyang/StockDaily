#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import time
import json
import sqlite3
from datetime import datetime, timedelta

def get_soxx_historical_price(target_date):
    """
    智能获取SOXX历史价格，使用多种策略避免被限制
    """
    # 策略1: 使用不同的User-Agent轮换
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    ]
    
    # 策略2: 尝试多个数据源
    data_sources = [
        {
            'name': 'yahoo_finance',
            'url_template': 'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1={start}&period2={end}&interval=1d',
            'parse_func': parse_yahoo_data
        }
    ]
    
    for i, source in enumerate(data_sources):
        try:
            print(f"尝试数据源 {source['name']}...")
            headers = {'User-Agent': user_agents[i % len(user_agents)]}
            
            # 转换日期为时间戳
            target_dt = datetime.strptime(target_date, '%Y-%m-%d')
            start_ts = int((target_dt - timedelta(days=1)).timestamp())
            end_ts = int((target_dt + timedelta(days=1)).timestamp())
            
            url = source['url_template'].format(
                symbol='SOXX',
                start=start_ts,
                end=end_ts
            )
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                price = source['parse_func'](response.json(), target_date)
                if price:
                    return price
                    
        except Exception as e:
            print(f"数据源 {source['name']} 失败: {e}")
            time.sleep(2)  # 避免连续请求
    
    return None

def parse_yahoo_data(data, target_date):
    """解析Yahoo Finance数据"""
    try:
        chart_data = data['chart']['result'][0]
        timestamps = chart_data['timestamp']
        prices = chart_data['indicators']['quote'][0]['close']
        
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
        for ts, price in zip(timestamps, prices):
            date_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
            if date_str == target_date and price is not None:
                return round(float(price), 3)
    except Exception as e:
        print(f"解析Yahoo数据失败: {e}")
    return None

def get_today_and_yesterday_prices():
    """获取今日和昨日的SOXX价格"""
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"获取日期: 昨日={yesterday}, 今日={today}")
    
    yesterday_price = get_soxx_historical_price(yesterday)
    today_price = get_soxx_historical_price(today)
    
    return yesterday_price, today_price

if __name__ == "__main__":
    yesterday_price, today_price = get_today_and_yesterday_prices()
    print(f"\nSOXX价格结果:")
    print(f"昨日价格: {yesterday_price}")
    print(f"今日价格: {today_price}")
    
    # 保存到结果文件
    result = {
        'yesterday_price': yesterday_price,
        'today_price': today_price,
        'fetched_at': datetime.now().isoformat()
    }
    
    with open('soxx_prices.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    print("\n价格数据已保存到 soxx_prices.json")
