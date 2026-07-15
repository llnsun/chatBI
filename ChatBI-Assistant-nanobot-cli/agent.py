#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票查询助手 - nanobot 版

支持自然语言查询股票历史数据、ARIMA 预测、布林带检测等功能。

运行: python agent.py "贵州茅台2025年的收盘价走势如何？"
"""

import asyncio
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

WORKSPACE = Path(__file__).resolve().parent

from nanobot.agent.hook import AgentHook, AgentHookContext
from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.config.loader import load_config
from nanobot.nanobot import Nanobot, _make_provider

from tools.exc_sql import ExcSQLTool
from tools.arima_stock import ArimaStockTool
from tools.boll_detection import BollDetectionTool
from tools.get_stock_realtime import GetStockRealtimeTool

DB_PATH = WORKSPACE / "stock_history.db"

# 预定义股票列表
DEFAULT_STOCKS = [
    ('600519.SH', '贵州茅台'),
    ('000858.SZ', '五粮液'),
    ('000776.SZ', '广发证券'),
    ('688981.SH', '中芯国际'),
]


class PrintHook(AgentHook):
    """打印工具调用信息的 Hook"""
    async def before_execute_tools(self, ctx: AgentHookContext) -> None:
        for tc in ctx.tool_calls:
            print(f"  >> {tc.name}: {str(tc.arguments)[:120]}")


def init_database():
    """初始化数据库，如果不存在则创建表结构并尝试拉取数据"""
    if DB_PATH.exists():
        print(f"[INFO] 数据库已存在: {DB_PATH}")
        return

    print(f"[INFO] 数据库不存在，开始初始化...")

    # 创建表结构
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("""
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
            )
        """)
        conn.commit()
        print(f"[INFO] 表结构创建完成")
    finally:
        conn.close()

    # 尝试从 Tushare 拉取数据
    token = os.environ.get("TUSHARE_TOKEN")
    if not token:
        print(f"[WARN] TUSHARE_TOKEN 未配置，无法自动拉取数据")
        print(f"[WARN] 工具会在查询时自动尝试拉取，或手动设置环境变量后重新运行")
        return

    print(f"[INFO] 开始从 Tushare 拉取预定义股票数据...")

    try:
        import tushare as ts
        import pandas as pd

        ts.set_token(token)
        pro = ts.pro_api()

        # 拉取最近一年的数据
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')

        total_count = 0
        for code, name in DEFAULT_STOCKS:
            print(f"  拉取 {name}({code})...")
            try:
                df = pro.daily(ts_code=code, start_date=start_date, end_date=end_date)
                if df.empty:
                    print(f"    [WARN] 无数据")
                    continue

                df = df[['trade_date', 'open', 'high', 'low', 'close',
                         'pre_close', 'change', 'pct_chg', 'vol', 'amount']].copy()
                df.columns = ['交易日期', '开盘价', '最高价', '最低价', '收盘价',
                              '昨收价', '涨跌额', '涨跌幅', '成交量', '成交额']
                df['股票名称'] = name
                df['股票代码'] = code
                df = df[['交易日期', '股票名称', '股票代码', '开盘价', '最高价',
                         '最低价', '收盘价', '昨收价', '涨跌额', '涨跌幅', '成交量', '成交额']]

                conn = sqlite3.connect(str(DB_PATH))
                try:
                    df.to_sql('stock_history', conn, if_exists='append', index=False)
                    count = len(df)
                    total_count += count
                    print(f"    [OK] {count} 条")
                finally:
                    conn.close()

            except Exception as e:
                print(f"    [ERROR] {e}")

        print(f"[INFO] 数据拉取完成，共 {total_count} 条")

    except Exception as e:
        print(f"[ERROR] 数据拉取失败: {e}")


def build_bot() -> Nanobot:
    """构建 Nanobot 实例"""
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not dashscope_key:
        print("[Error] DASHSCOPE_API_KEY not set")
        sys.exit(1)

    config = load_config(WORKSPACE / "config.json")
    config.providers.dashscope.api_key = dashscope_key
    config.agents.defaults.workspace = str(WORKSPACE)

    provider = _make_provider(config)
    defaults = config.agents.defaults

    loop = AgentLoop(
        bus=MessageBus(),
        provider=provider,
        workspace=WORKSPACE,
        model=defaults.model,
        max_iterations=defaults.max_tool_iterations,
        context_window_tokens=defaults.context_window_tokens,
        max_tool_result_chars=defaults.max_tool_result_chars,
        web_config=config.tools.web,
        exec_config=config.tools.exec,
        restrict_to_workspace=False,
        timezone=defaults.timezone,
    )

    # 注册自定义工具
    loop.tools.register(ExcSQLTool(DB_PATH))
    loop.tools.register(ArimaStockTool(DB_PATH))
    loop.tools.register(BollDetectionTool(DB_PATH))
    loop.tools.register(GetStockRealtimeTool(DB_PATH))

    return Nanobot(loop)


async def main():
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "贵州茅台2025年的收盘价走势如何？"

    # 初始化数据库
    init_database()

    print(f"\n股票查询助手 (nanobot)")
    print(f"问题: {question}\n")

    bot = build_bot()
    result = await bot.run(question, session_key="stock:run", hooks=[PrintHook()])

    print(f"\n{'='*60}")
    print(f"回答: {result.content}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
