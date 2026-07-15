"""SQL 查询工具 - nanobot 版"""

import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text

from nanobot.agent.tools.base import Tool

from utils.stock_resolver import resolve_stock_code, query_with_auto_fetch
from utils.chart import generate_chart_png


class ExcSQLTool(Tool):
    """SQL 查询工具，执行 SQL 并自动可视化"""

    def __init__(self, db_path: Path):
        self._db_path = db_path

    @property
    def name(self) -> str:
        return "exc_sql"

    @property
    def description(self) -> str:
        return "执行 SQL 查询股票历史数据，自动返回表格和可视化图表。如果数据库中没有数据，会自动从 Tushare 拉取。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sql_input": {
                    "type": "string",
                    "description": "要执行的 SQL 语句（SELECT）",
                }
            },
            "required": ["sql_input"],
        }

    @property
    def read_only(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> str:
        sql_input = kwargs.get("sql_input", "").strip()
        if not sql_input:
            return "错误：SQL 语句不能为空"

        print(f'[DEBUG] exc_sql: {sql_input}')

        # 尝试从 SQL 中提取股票代码，用于自动拉取
        actual_code = None
        stock_name = None
        start_date = None
        end_date = None

        sql_upper = sql_input.upper()
        if '股票代码' in sql_input or 'STOCK_CODE' in sql_upper:
            code_match = re.search(r"['\"](\d{6}\.(SH|SZ))['\"]", sql_input)
            if code_match:
                actual_code = code_match.group(1)
                stock_name = actual_code

            date_match = re.search(r"交易日期\s*>=\s*['\"](\d{8})['\"]", sql_input)
            if date_match:
                start_date = date_match.group(1)

            date_match2 = re.search(r"交易日期\s*<=\s*['\"](\d{8})['\"]", sql_input)
            if date_match2:
                end_date = date_match2.group(1)

        if actual_code and stock_name:
            if not start_date:
                start_date = '20200101'
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')

            df = query_with_auto_fetch(self._db_path, sql_input, actual_code, stock_name, start_date, end_date)
        else:
            engine = create_engine(f'sqlite:///{self._db_path}')
            df = pd.read_sql(text(sql_input), engine)

        print(f'[DEBUG] 查询结果: {len(df)}条记录')

        if df.empty:
            return "查询结果为空"

        # 判断是否有股票名称列
        stock_col = None
        for col in df.columns:
            if '股票' in col and '名称' in col:
                stock_col = col
                break

        if stock_col is not None and df[stock_col].nunique() > 1:
            md_parts = []
            for sname in df[stock_col].unique():
                stock_df = df[df[stock_col] == sname]
                md_parts.append(f"**股票：{sname}**")
                if len(stock_df) <= 10:
                    md_parts.append(stock_df.to_markdown(index=False))
                else:
                    md_parts.append(stock_df.head(5).to_markdown(index=False))
                    md_parts.append(stock_df.tail(5).to_markdown(index=False))
                    md_parts.append(stock_df.describe().to_markdown())
                md_parts.append("")
            md = "\n".join(md_parts)
        else:
            if len(df) <= 10:
                md = df.to_markdown(index=False)
            else:
                md_head = df.head(5).to_markdown(index=False)
                md_tail = df.tail(5).to_markdown(index=False)
                md_desc = df.describe().to_markdown()
                md = f"**前5行数据：**\n{md_head}\n\n**后5行数据：**\n{md_tail}\n\n**描述统计：**\n{md_desc}"

        if len(df) <= 1:
            return md

        save_dir = self._db_path.parent / 'image_show'
        save_dir.mkdir(exist_ok=True)
        filename = f'chart_{int(time.time() * 1000)}.png'
        save_path = save_dir / filename

        generate_chart_png(df, save_path)

        img_md = f'![图表]({save_path})'
        return f"{md}\n\n{img_md}"
