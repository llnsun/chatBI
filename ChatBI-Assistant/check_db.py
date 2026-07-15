import sqlite3

db_path = r'd:\work\AI-APP\AiDemo\ChatBI\ChatBI-Assistant\stock_history.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查看所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("数据库中的表:", tables)

# 如果有表，查看表结构
if tables:
    for table in tables:
        table_name = table[0]
        print(f"\n表 '{table_name}' 的结构:")
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col}")
        
        # 查看数据条数
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  数据条数: {count}")

conn.close()
