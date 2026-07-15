"""实时股票数据查询工具 - nanobot 版"""

import os
import time
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from nanobot.agent.tools.base import Tool

from utils.stock_resolver import resolve_stock_code, fetch_real_stock_name

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class GetStockRealtimeTool(Tool):
    """通过 Tushare API 获取股票实时行情数据"""

    def __init__(self, db_path: Path):
        self._db_path = db_path

    @property
    def name(self) -> str:
        return "get_stock_realtime"

    @property
    def description(self) -> str:
        return "通过 Tushare API 获取股票实时行情数据，支持股票代码或股票名称"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ts_code": {
                    "type": "string",
                    "description": "股票代码或股票名称，如 600519.SH 或 贵州茅台",
                }
            },
            "required": ["ts_code"],
        }

    @property
    def read_only(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> str:
        ts_code = kwargs.get("ts_code", "")
        if not ts_code:
            return "错误：请提供股票代码或名称"

        actual_code, stock_name = resolve_stock_code(ts_code)
        print(f'[DEBUG] get_stock_realtime: ts_code={ts_code}, actual_code={actual_code}')

        import tushare as ts

        token = os.getenv('TUSHARE_TOKEN')
        if not token:
            return "错误：TUSHARE_TOKEN 环境变量未配置，无法获取实时数据"

        ts.set_token(token)
        pro = ts.pro_api()

        real_name = fetch_real_stock_name(actual_code)
        if real_name != stock_name:
            stock_name = real_name

        try:
            now = pd.Timestamp.now()
            five_days_ago = (now - pd.Timedelta(days=5)).strftime('%Y%m%d')
            today = now.strftime('%Y%m%d')

            df = pro.daily(ts_code=actual_code, start_date=five_days_ago, end_date=today)
            if df.empty:
                return f"无法获取 {stock_name}({actual_code}) 的实时数据，可能原因：\n1. 非交易日\n2. Tushare 接口限制\n3. 股票代码不正确"

            df = df.sort_values('trade_date', ascending=False).head(1)
            row = df.iloc[0]

            md = f"""| 指标 | 数值 |
|------|------|
| 股票名称 | {stock_name} |
| 股票代码 | {actual_code} |
| 交易日期 | {row['trade_date']} |
| 开盘价 | {row['open']:.2f} |
| 最高价 | {row['high']:.2f} |
| 最低价 | {row['low']:.2f} |
| 收盘价 | {row['close']:.2f} |
| 昨收价 | {row['pre_close']:.2f} |
| 涨跌额 | {row['change']:.2f} |
| 涨跌幅 | {row['pct_chg']:.2f}% |
| 成交量(手) | {row['vol']:.0f} |
| 成交额(千元) | {row['amount']:.0f} |"""

            save_dir = self._db_path.parent / 'image_show'
            save_dir.mkdir(exist_ok=True)
            filename = f'realtime_{int(time.time() * 1000)}.png'
            save_path = save_dir / filename

            fig, ax = plt.subplots(figsize=(10, 6))
            categories = ['开盘价', '最高价', '最低价', '收盘价']
            values = [row['open'], row['high'], row['low'], row['close']]
            colors = ['#1f77b4', '#2ca02c', '#d62728', '#ff7f0e']

            ax.bar(categories, values, color=colors)
            for i, v in enumerate(values):
                ax.text(i, v, f'{v:.2f}', ha='center', va='bottom', fontsize=10)

            ax.set_title(f'{stock_name}({actual_code}) 实时行情', fontsize=14, fontweight='bold')
            ax.set_ylabel('价格（元）', fontsize=11)
            plt.tight_layout()
            plt.savefig(save_path, dpi=120)
            plt.close()

            img_md = f'![实时行情]({save_path})'
            return f"**{stock_name}({actual_code}) 实时行情**\n\n{md}\n\n{img_md}"

        except Exception as e:
            import traceback
            print(f'[ERROR] get_stock_realtime异常: {str(e)}')
            print(traceback.format_exc())
            return f"获取实时数据失败：{str(e)}\n\n请检查：\n1. Tushare token 是否配置正确\n2. 网络连接是否正常\n3. 是否安装了 tushare 库（pip install tushare）"
