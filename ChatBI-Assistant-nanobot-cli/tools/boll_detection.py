# -*- coding: utf-8 -*-
"""布林带超买超卖检测工具 - nanobot 版"""

import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from nanobot.agent.tools.base import Tool
from utils.stock_resolver import resolve_stock_code, fetch_and_store_stock_data

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "SimSun", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False


class BollDetectionTool(Tool):
    """布林带超买超卖检测工具"""

    def __init__(self, db_path: Path):
        self._db_path = db_path

    @property
    def name(self) -> str:
        return "boll_detection"

    @property
    def description(self) -> str:
        return "使用布林带（MA20 ± 2σ）检测股票的超买超卖信号。需要至少 20 条历史数据。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ts_code": {
                    "type": "string",
                    "description": "股票代码或名称，如 600519.SH 或 贵州茅台",
                },
                "start_date": {
                    "type": "string",
                    "description": "开始日期，格式 YYYYMMDD，默认一年前",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式 YYYYMMDD，默认今天",
                },
            },
            "required": ["ts_code"],
        }

    @property
    def read_only(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> str:
        ts_code = kwargs.get("ts_code", "")
        start_date = kwargs.get("start_date", "")
        end_date = kwargs.get("end_date", "")

        if not ts_code:
            return "错误：请提供股票代码或名称"

        actual_code, stock_name = resolve_stock_code(ts_code)
        print(f'[DEBUG] boll_detection: ts_code={ts_code}, actual_code={actual_code}')

        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')

        WINDOW = 20
        NUM_STD = 2

        conn = sqlite3.connect(str(self._db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 交易日期, 收盘价 FROM stock_history
                WHERE 股票代码 = ? AND 交易日期 >= ? AND 交易日期 <= ?
                ORDER BY 交易日期 ASC
            """, (actual_code, start_date, end_date))
            result = cursor.fetchall()

            # 数据不足，尝试自动拉取
            if len(result) < WINDOW:
                print(f'[INFO] 数据不足({len(result)}条)，尝试从 Tushare 拉取')
                fetched = fetch_and_store_stock_data(
                    self._db_path, actual_code, stock_name, start_date, end_date
                )
                if fetched > 0:
                    cursor.execute("""
                        SELECT 交易日期, 收盘价 FROM stock_history
                        WHERE 股票代码 = ? AND 交易日期 >= ? AND 交易日期 <= ?
                        ORDER BY 交易日期 ASC
                    """, (actual_code, start_date, end_date))
                    result = cursor.fetchall()

            if len(result) < WINDOW:
                return f"{stock_name}({actual_code}) 数据不足（仅 {len(result)} 条），无法计算布林带（至少需要 {WINDOW} 条）。"

            df = pd.DataFrame(result, columns=["日期", "收盘价"])
            df["日期"] = pd.to_datetime(df["日期"], format='%Y%m%d')
            close = df["收盘价"].values

            # 计算布林带
            ma = pd.Series(close).rolling(window=WINDOW).mean().values
            std = pd.Series(close).rolling(window=WINDOW).std().values
            upper_band = ma + (std * NUM_STD)
            lower_band = ma - (std * NUM_STD)

            # 检测超买超卖（从 WINDOW-1 开始，因为前面数据不足计算 MA）
            valid_start = WINDOW - 1
            overbought_dates = []
            overbought_prices = []
            oversold_dates = []
            oversold_prices = []

            for i in range(valid_start, len(close)):
                if close[i] >= upper_band[i]:
                    overbought_dates.append(df["日期"].iloc[i])
                    overbought_prices.append(close[i])
                elif close[i] <= lower_band[i]:
                    oversold_dates.append(df["日期"].iloc[i])
                    oversold_prices.append(close[i])

            # 生成图表
            save_dir = self._db_path.parent / 'image_show'
            save_dir.mkdir(exist_ok=True)
            filename = f'boll_{int(time.time() * 1000)}.png'
            save_path = save_dir / filename

            fig, ax = plt.subplots(figsize=(14, 7))

            # 有效数据范围
            valid_dates = df["日期"].iloc[valid_start:]
            valid_close = close[valid_start:]
            valid_ma = ma[valid_start:]
            valid_upper = upper_band[valid_start:]
            valid_lower = lower_band[valid_start:]

            ax.plot(valid_dates, valid_close, label="收盘价", color="black", linewidth=1)
            ax.plot(valid_dates, valid_ma, label="中轨(MA20)", color="blue", linestyle="--", linewidth=1)
            ax.plot(valid_dates, valid_upper, label="上轨(+2σ)", color="red", linestyle="--", linewidth=1)
            ax.plot(valid_dates, valid_lower, label="下轨(-2σ)", color="green", linestyle="--", linewidth=1)

            if overbought_dates:
                ax.scatter(overbought_dates, overbought_prices, color="red", s=60,
                           label=f"超买信号({len(overbought_dates)}个)", marker="v", zorder=5)
            if oversold_dates:
                ax.scatter(oversold_dates, oversold_prices, color="green", s=60,
                           label=f"超卖信号({len(oversold_dates)}个)", marker="^", zorder=5)

            ax.set_xlabel("日期")
            ax.set_ylabel("收盘价（元）")
            ax.set_title(f"{stock_name}({actual_code}) 布林带分析", fontsize=14, fontweight="bold")
            ax.legend()
            ax.grid(True, linestyle="--", alpha=0.6)
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(save_path, dpi=120)
            plt.close()

            # 构建输出
            summary = (
                f"**{stock_name}({actual_code}) 布林带检测结果**\n\n"
                f"- 分析区间：{start_date} ~ {end_date}\n"
                f"- 有效交易日：{len(valid_close)} 天\n"
                f"- 超买信号（收盘价 > 上轨）：{len(overbought_dates)} 个\n"
                f"- 超卖信号（收盘价 < 下轨）：{len(oversold_dates)} 个\n"
                f"- 当前收盘价：{close[-1]:.2f}，最新MA20：{valid_ma[-1]:.2f}\n"
            )

            # 超买详情
            if overbought_dates:
                summary += "\n**超买交易日（卖出信号）：**\n| 日期 | 收盘价 | 上轨 |\n|------|--------|------|\n"
                for i, d in enumerate(overbought_dates[:10]):
                    idx = df[df["日期"] == d].index[0]
                    summary += f"| {d.strftime('%Y-%m-%d')} | {overbought_prices[i]:.2f} | {upper_band[idx]:.2f} |\n"
                if len(overbought_dates) > 10:
                    summary += f"| ... | ... | ... |\n"

            if oversold_dates:
                summary += "\n**超卖交易日（买入信号）：**\n| 日期 | 收盘价 | 下轨 |\n|------|--------|------|\n"
                for i, d in enumerate(oversold_dates[:10]):
                    idx = df[df["日期"] == d].index[0]
                    summary += f"| {d.strftime('%Y-%m-%d')} | {oversold_prices[i]:.2f} | {lower_band[idx]:.2f} |\n"
                if len(oversold_dates) > 10:
                    summary += f"| ... | ... | ... |\n"

            img_md = f'![布林带分析]({save_path})'
            return f"{summary}\n{img_md}"

        finally:
            conn.close()
