#!/usr/bin/env python
# coding: utf-8

import os
import tushare as ts
import pandas as pd
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
            df.columns = ['交易日期', '股票名称', '股票代码', '开盘价', '最高价', '最低价', '收盘价', '昨收价', '涨跌额', '涨跌幅(%)', '成交量(手)', '成交额(千元)']
            
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
    
    # 保存到Excel文件
    output_file = r'd:\work\AI应用\AiDemo\ChatBI\ChatBI助手\stock_history_data.xlsx'
    combined_df.to_excel(output_file, index=False, sheet_name='股票历史价格')
    
    print(f"\n数据获取完成！")
    print(f"总共获取 {len(combined_df)} 条记录")
    print(f"数据已保存到：{output_file}")
    print(f"\n数据预览（前10行）：")
    print(combined_df.head(10))
else:
    print("错误：未能获取到任何股票数据")
