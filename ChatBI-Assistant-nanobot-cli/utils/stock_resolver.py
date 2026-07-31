# -*- coding: utf-8 -*-
"""股票代码解析与自动拉取工具"""

import os
import sqlite3
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

STOCK_NAME_TO_CODE = {
    '贵州茅台': '600519.SH',
    '五粮液': '000858.SZ',
    '广发证券': '000776.SZ',
    '中芯国际': '688981.SH',
}

CODE_TO_NAME = {v: k for k, v in STOCK_NAME_TO_CODE.items()}


def resolve_stock_code(ts_code):
    """将股票名称或代码统一解析为 (actual_code, stock_name)"""
    if ts_code in STOCK_NAME_TO_CODE:
        return STOCK_NAME_TO_CODE[ts_code], ts_code
    elif ts_code in CODE_TO_NAME:
        return ts_code, CODE_TO_NAME[ts_code]
    return ts_code, ts_code


def fetch_real_stock_name(actual_code):
    """通过 Tushare stock_basic 接口查询股票的真实名称"""
    try:
        import tushare as ts
        token = os.getenv('TUSHARE_TOKEN')
        if not token:
            return actual_code
        ts.set_token(token)
        pro = ts.pro_api()
        info = pro.stock_basic(ts_code=actual_code, fields='ts_code,name')
        if info is not None and not info.empty:
            return info['name'].iloc[0]
    except Exception as e:
        print(f'[WARN] 查询股票名称失败: {e}')
    return actual_code


def fetch_and_store_stock_data(db_path, actual_code, stock_name, start_date, end_date):
    """通过 Tushare 拉取股票历史数据并写入 SQLite，返回拉取的记录数"""
    try:
        import tushare as ts
        token = os.getenv('TUSHARE_TOKEN')
        if not token:
            print(f'[WARN] TUSHARE_TOKEN 未配置，无法拉取 {stock_name}({actual_code}) 的数据')
            return 0

        ts.set_token(token)
        pro = ts.pro_api()

        real_name = fetch_real_stock_name(actual_code)
        if real_name != stock_name:
            print(f'[INFO] 股票名称修正: {stock_name} -> {real_name}')
            stock_name = real_name

        df = pro.daily(ts_code=actual_code, start_date=start_date, end_date=end_date)
        if df.empty:
            print(f'[WARN] Tushare 返回空数据: {stock_name}({actual_code}) {start_date}~{end_date}')
            return 0

        df = df[['trade_date', 'open', 'high', 'low', 'close',
                 'pre_close', 'change', 'pct_chg', 'vol', 'amount']].copy()
        df.columns = ['交易日期', '开盘价', '最高价', '最低价', '收盘价',
                      '昨收价', '涨跌额', '涨跌幅', '成交量', '成交额']
        df['股票名称'] = stock_name
        df['股票代码'] = actual_code
        df = df[['交易日期', '股票名称', '股票代码', '开盘价', '最高价',
                 '最低价', '收盘价', '昨收价', '涨跌额', '涨跌幅', '成交量', '成交额']]

        conn = sqlite3.connect(str(db_path))
        try:
            df.to_sql('stock_history', conn, if_exists='append', index=False)
            count = len(df)
            print(f'[INFO] 已从 Tushare 拉取并写入 {count} 条 {stock_name}({actual_code}) 数据')
            return count
        finally:
            conn.close()
    except Exception as e:
        print(f'[ERROR] fetch_and_store_stock_data 失败: {e}')
        return 0


def query_with_auto_fetch(db_path, sql, actual_code, stock_name, start_date, end_date):
    """执行 SQL 查询；如果结果为空，自动从 Tushare 拉取后重试"""
    engine = create_engine(f'sqlite:///{db_path}')
    df = pd.read_sql(text(sql), engine)

    if not df.empty:
        return df

    print(f'[INFO] 数据库无结果，尝试从 Tushare 自动拉取 {stock_name}({actual_code})')
    fetched = fetch_and_store_stock_data(db_path, actual_code, stock_name, start_date, end_date)
    if fetched > 0:
        engine = create_engine(f'sqlite:///{db_path}')
        df = pd.read_sql(text(sql), engine)

    return df
