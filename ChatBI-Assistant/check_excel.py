import pandas as pd

# 读取 Excel 文件
excel_path = r'd:\work\AI-APP\AiDemo\ChatBI\ChatBI-Assistant\stock_history_data.xlsx'
df = pd.read_excel(excel_path)

print("Excel 文件结构:")
print(f"数据条数：{len(df)}")
print(f"列名：{df.columns.tolist()}")
print("\n前 10 条数据:")
print(df.head(10))
print("\n数据时间范围:")
print(f"最早日期：{df['交易日期'].min()}")
print(f"最晚日期：{df['交易日期'].max()}")
print("\n包含的股票:")
print(df[['股票名称', '股票代码']].drop_duplicates())
