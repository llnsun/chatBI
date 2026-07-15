import pandas as pd
import sqlite3
import os

# 读取 Excel 文件
excel_path = r'd:\work\AI-APP\AiDemo\ChatBI\ChatBI-Assistant\stock_history_data.xlsx'
print("正在读取 Excel 文件...")
df = pd.read_excel(excel_path)

print(f"读取到 {len(df)} 条数据")
print(f"Excel 列名：{df.columns.tolist()}")

# 删除旧数据库
db_path = r'd:\work\AI-APP\AiDemo\ChatBI\ChatBI-Assistant\stock_history.db'
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"\n已删除旧数据库文件")

# 连接数据库
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 创建表
print("创建 stock_history 表...")
cursor.execute('''
CREATE TABLE stock_history (
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
)
''')

# 转换数据格式
print("\n正在转换数据格式...")
df['交易日期'] = df['交易日期'].astype(str)

# 处理日期格式（从 20200102 转换为 2020-01-02）
def format_date(date_str):
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return date_str

df['交易日期'] = df['交易日期'].apply(format_date)

# 插入数据
print("正在插入数据...")
insert_count = 0
error_count = 0

for index, row in df.iterrows():
    try:
        # 获取涨跌幅，处理不同的列名
        zhangdiefu = row.get('涨跌幅 (%)')
        if zhangdiefu is None or (isinstance(zhangdiefu, float) and pd.isna(zhangdiefu)):
            zhangdiefu = row.get('涨跌幅')
        
        # 获取成交量，处理不同的列名
        chengjiaoliang = row.get('成交量 (手)')
        if chengjiaoliang is None or (isinstance(chengjiaoliang, float) and pd.isna(chengjiaoliang)):
            chengjiaoliang = row.get('成交量')
        
        # 获取成交额，处理不同的列名
        chengjiaoe = row.get('成交额 (千元)')
        if chengjiaoe is None or (isinstance(chengjiaoe, float) and pd.isna(chengjiaoe)):
            chengjiaoe = row.get('成交额')
        
        cursor.execute('''
        INSERT INTO stock_history (交易日期，股票名称，股票代码，开盘价，最高价，最低价，收盘价，昨收价，涨跌额，涨跌幅，成交量，成交额)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(row['交易日期']),
            str(row['股票名称']),
            str(row['股票代码']),
            float(row['开盘价']) if pd.notna(row.get('开盘价')) else None,
            float(row['最高价']) if pd.notna(row.get('最高价')) else None,
            float(row['最低价']) if pd.notna(row.get('最低价')) else None,
            float(row['收盘价']) if pd.notna(row.get('收盘价')) else None,
            float(row['昨收价']) if pd.notna(row.get('昨收价')) else None,
            float(row['涨跌额']) if pd.notna(row.get('涨跌额')) else None,
            float(zhangdiefu) if zhangdiefu is not None and pd.notna(zhangdiefu) else None,
            float(chengjiaoliang) if chengjiaoliang is not None and pd.notna(chengjiaoliang) else None,
            float(chengjiaoe) if chengjiaoe is not None and pd.notna(chengjiaoe) else None
        ))
        insert_count += 1
    except Exception as e:
        error_count += 1
        if error_count <= 5:  # 只显示前 5 个错误
            print(f"插入第 {index} 行数据时出错：{e}")
        continue

conn.commit()

# 验证结果
cursor.execute("SELECT COUNT(*) FROM stock_history")
total_count = cursor.fetchone()[0]
print(f"\n导入完成!")
print(f"成功插入：{insert_count} 条")
print(f"失败：{error_count} 条")
print(f"数据库总数据量：{total_count} 条")

# 查看 2025 年的数据
cursor.execute("SELECT COUNT(*) FROM stock_history WHERE 交易日期 LIKE '2025%'")
count_2025 = cursor.fetchone()[0]
print(f"\n2025 年数据：{count_2025} 条")

# 查看 2026 年的数据
cursor.execute("SELECT COUNT(*) FROM stock_history WHERE 交易日期 LIKE '2026%'")
count_2026 = cursor.fetchone()[0]
print(f"2026 年数据：{count_2026} 条")

# 显示最新的日期
cursor.execute("SELECT MAX(交易日期) FROM stock_history")
max_date = cursor.fetchone()[0]
print(f"最新日期：{max_date}")

# 查看每个股票的数据量
cursor.execute("SELECT 股票名称，股票代码，COUNT(*) as count FROM stock_history GROUP BY 股票名称，股票代码")
stocks = cursor.fetchall()
print(f"\n各股票数据量:")
for stock in stocks:
    print(f"  - {stock[0]} ({stock[1]}): {stock[2]} 条")

conn.close()
print("\n数据库导入完成!")
