#!/usr/bin/env python
# coding: utf-8

import os
import tushare as ts
import pandas as pd
import sqlite3
from datetime import datetime

# 设置tushare token（从环境变量读取）
token = os.getenv('TUSHARE_TOKEN')

# 验证token是否设置成功
if not token:
    print("错误：未设置TUSHARE_TOKEN环境变量")
    print("请设置环境变量：")
    print("  Windows: set TUSHARE_TOKEN=你的token")
    print("  Linux/Mac: export TUSHARE_TOKEN=你的token")
    exit(1)
    
ts.set_token(token)
pro = ts.pro_api()

# 定义股票列表（ts_code格式）
stocks = {
    '贵州茅台': '600519.SH',
    '五粮液': '000858.SZ',
    '广发证券': '000776.SZ',
    '中芯国际': '688981.SH'
}

# 设置时间范围
start_date = '20200101'
end_date = datetime.now().strftime('%Y%m%d')

print(f"开始获取股票数据，时间范围：{start_date} 至 {end_date}")

# 存储所有股票数据
all_data = []

for stock_name, ts_code in stocks.items():
    print(f"正在获取 {stock_name} ({ts_code}) 的数据...")
    try:
        # 获取日线行情数据
        df = pro.daily(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )
        
        if not df.empty:
            # 添加股票名称列
            df['股票名称'] = stock_name
            df['ts_code'] = ts_code
            
            # 选择需要的列
            df = df[['trade_date', '股票名称', 'ts_code', 'open', 'high', 'low', 'close', 'pre_close', 'change', 'pct_chg', 'vol', 'amount']]
            
            # 重命名列名为中文
            df.columns = ['交易日期', '股票名称', '股票代码', '开盘价', '最高价', '最低价', '收盘价', '昨收价', '涨跌额', '涨跌幅', '成交量', '成交额']
            
            all_data.append(df)
            print(f"  成功获取 {len(df)} 条记录")
        else:
            print(f"  警告：未获取到 {stock_name} 的数据")
            
    except Exception as e:
        print(f"  错误：获取 {stock_name} 数据失败 - {str(e)}")

# 合并所有数据
if all_data:
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # 按照交易日期从小到大排序
    combined_df = combined_df.sort_values(by='交易日期', ascending=True)
    
    # 重置索引
    combined_df = combined_df.reset_index(drop=True)
    
    print(f"\n数据获取完成！总共获取 {len(combined_df)} 条记录")
    
    # 生成 SQL 建表语句
    create_table_sql = """
CREATE TABLE IF NOT EXISTS stock_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    交易日期 TEXT NOT NULL,
    股票名称 TEXT NOT NULL,
    股票代码 TEXT NOT NULL,
    开盘价 REAL,
    最高价 REAL,
    最低价 REAL,
    收盘价 REAL,
    昨收价 REAL,
    涨跌额 REAL,
    涨跌幅 REAL,
    成交量 REAL,
    成交额 REAL
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_trade_date ON stock_history(交易日期);
CREATE INDEX IF NOT EXISTS idx_stock_code ON stock_history(股票代码);
CREATE INDEX IF NOT EXISTS idx_stock_name ON stock_history(股票名称);
"""
    
    # 保存 SQL 建表语句到文件
    sql_file = r'd:\work\AI应用\AiDemo\ChatBI\ChatBI-Assistant\create_table.sql'
    with open(sql_file, 'w', encoding='utf-8') as f:
        f.write(create_table_sql)
    print(f"SQL 建表语句已保存到：{sql_file}")
    
    # 保存到 SQLite 数据库
    db_file = r'd:\work\AI应用\AiDemo\ChatBI\ChatBI-Assistant\stock_history.db'
    
    # 连接 SQLite 数据库
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    try:
        # 执行建表语句
        cursor.executescript(create_table_sql)
        print(f"\n数据库表创建成功！")
        
        # 插入数据
        print("正在插入数据到 SQLite 数据库...")
        combined_df.to_sql('stock_history', conn, if_exists='append', index=False)
        
        # 验证数据
        cursor.execute("SELECT COUNT(*) FROM stock_history")
        count = cursor.fetchone()[0]
        print(f"数据插入完成！数据库中共有 {count} 条记录")
        
        # 显示数据预览
        print("\n数据预览（前10行）：")
        cursor.execute("SELECT * FROM stock_history ORDER BY 交易日期 LIMIT 10")
        rows = cursor.fetchall()
        for row in rows:
            print(row)
            
    except Exception as e:
        print(f"数据库操作错误：{str(e)}")
    finally:
        conn.close()
    
    print(f"\nSQLite 数据库已保存到：{db_file}")
    
else:
    print("错误：未能获取到任何股票数据")
