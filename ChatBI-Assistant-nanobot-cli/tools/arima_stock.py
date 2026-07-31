# -*- coding: utf-8 -*-
"""ARIMA 价格预测工具 - nanobot 版"""

import sqlite3
import time
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

from nanobot.agent.tools.base import Tool
from utils.stock_resolver import resolve_stock_code, fetch_and_store_stock_data

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "SimSun", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False


class ArimaStockTool(Tool):
    """ARIMA 时间序列预测工具"""

    def __init__(self, db_path: Path):
        self._db_path = db_path

    @property
    def name(self) -> str:
        return "arima_stock"

    @property
    def description(self) -> str:
        return "使用 ARIMA 模型预测股票未来 N 天的收盘价走势。需要至少 30 条历史数据。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ts_code": {
                    "type": "string",
                    "description": "股票代码或名称，如 600519.SH 或 贵州茅台",
                },
                "n": {
                    "type": "integer",
                    "description": "预测天数，默认 5，范围 1-365",
                    "default": 5,
                },
            },
            "required": ["ts_code"],
        }

    @property
    def read_only(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> str:
        ts_code = kwargs.get("ts_code", "")
        n = kwargs.get("n", 5)

        if not ts_code:
            return "错误：请提供股票代码或名称"
        if not isinstance(n, int) or n <= 0 or n > 365:
            return "错误：预测天数(n)必须是 1-365 之间的整数"

        actual_code, stock_name = resolve_stock_code(ts_code)
        print(f'[DEBUG] arima_stock: ts_code={ts_code}, actual_code={actual_code}, n={n}')

        warnings.filterwarnings("ignore")

        # 查询历史数据
        conn = sqlite3.connect(str(self._db_path))
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=730)).strftime('%Y%m%d')

            cursor = conn.cursor()
            cursor.execute("""
                SELECT 交易日期, 收盘价 FROM stock_history
                WHERE 股票代码 = ? AND 交易日期 >= ?
                ORDER BY 交易日期 ASC
            """, (actual_code, start_date))
            result = cursor.fetchall()

            # 数据不足，尝试自动拉取
            if len(result) < 30:
                print(f'[INFO] 历史数据不足({len(result)}条)，尝试从 Tushare 拉取')
                fetched = fetch_and_store_stock_data(
                    self._db_path, actual_code, stock_name, start_date,
                    datetime.now().strftime('%Y%m%d')
                )
                if fetched > 0:
                    cursor.execute("""
                        SELECT 交易日期, 收盘价 FROM stock_history
                        WHERE 股票代码 = ? AND 交易日期 >= ?
                        ORDER BY 交易日期 ASC
                    """, (actual_code, start_date))
                    result = cursor.fetchall()

            if not result:
                return f"找不到 {stock_name}({actual_code}) 的历史数据。请检查股票代码是否正确，或配置 TUSHARE_TOKEN 后重试。"

            if len(result) < 10:
                return f"{stock_name}({actual_code}) 历史数据不足（仅 {len(result)} 条），无法进行 ARIMA 预测（至少需要 10 条）。"

            df = pd.DataFrame(result, columns=["日期", "收盘价"])
            df["日期"] = pd.to_datetime(df["日期"], format='%Y%m%d')
            close_prices = df["收盘价"].values

            # ARIMA 建模
            try:
                model = ARIMA(close_prices, order=(5, 1, 5))
                fitted_model = model.fit()
            except Exception:
                print('[WARN] ARIMA(5,1,5) 失败，降级为 ARIMA(2,1,2)')
                model = ARIMA(close_prices, order=(2, 1, 2))
                fitted_model = model.fit()

            forecast_result = fitted_model.forecast(steps=n)
            conf_int = fitted_model.get_forecast(steps=n).conf_int()

            # 生成预测日期
            last_date = df["日期"].iloc[-1]
            future_dates = [last_date + timedelta(days=i + 1) for i in range(n)]

            # 构建预测表格
            avg_price = np.mean(forecast_result)
            max_price = np.max(forecast_result)
            min_price = np.min(forecast_result)
            first_price = forecast_result[0]
            last_pred_price = forecast_result[-1]
            change_pct = ((last_pred_price - first_price) / first_price * 100) if first_price != 0 else 0

            summary = (
                f"**{stock_name}({actual_code}) ARIMA 预测摘要**\n\n"
                f"- 预测天数：{n} 天\n"
                f"- 历史数据：{len(df)} 条交易记录\n"
                f"- 预测平均价：{avg_price:.2f}\n"
                f"- 预测最高价：{max_price:.2f}\n"
                f"- 预测最低价：{min_price:.2f}\n"
                f"- 变化幅度：{change_pct:+.2f}%\n"
            )

            # 预测详情表
            table_rows = "| 日期 | 预测收盘价 | 下限(95%) | 上限(95%) |\n"
            table_rows += "|------|-----------|----------|----------|\n"
            for i in range(n):
                table_rows += (
                    f"| {future_dates[i].strftime('%Y-%m-%d')} "
                    f"| {forecast_result[i]:.2f} "
                    f"| {conf_int[i, 0]:.2f} "
                    f"| {conf_int[i, 1]:.2f} |\n"
                )

            # 生成图表
            save_dir = self._db_path.parent / 'image_show'
            save_dir.mkdir(exist_ok=True)
            filename = f'arima_{int(time.time() * 1000)}.png'
            save_path = save_dir / filename

            fig, ax = plt.subplots(figsize=(12, 6))

            # 历史数据
            ax.plot(df["日期"], df["收盘价"], label="历史收盘价", color="#1f77b4", linewidth=2)

            # 预测数据
            ax.plot(future_dates, forecast_result, label="预测收盘价", color="#ff7f0e",
                    linestyle="--", linewidth=2, marker="o")

            # 置信区间
            ax.fill_between(future_dates, conf_int[:, 0], conf_int[:, 1],
                            alpha=0.15, color="#ff7f0e", label="95% 置信区间")

            ax.set_xlabel("日期")
            ax.set_ylabel("收盘价（元）")
            ax.set_title(f"{stock_name}({actual_code}) ARIMA 预测", fontsize=14, fontweight="bold")
            ax.legend()
            ax.grid(True, linestyle="--", alpha=0.6)
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(save_path, dpi=120)
            plt.close()

            img_md = f'![ARIMA预测]({save_path})'
            return f"{summary}\n{table_rows}\n{img_md}"

        finally:
            conn.close()
