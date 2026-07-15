#!/usr/bin/env python
# coding: utf-8

import os
import asyncio
import sqlite3
from typing import Optional
import dashscope
from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI
import pandas as pd
from sqlalchemy import create_engine, text
from qwen_agent.tools.base import BaseTool, register_tool
import matplotlib.pyplot as plt
import io
import base64
import time
import numpy as np
from datetime import datetime, timedelta

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

ROOT_RESOURCE = os.path.join(os.path.dirname(__file__), 'resource')

dashscope.api_key = os.getenv('DASHSCOPE_API_KEY', '')
dashscope.timeout = 30

system_prompt = """我是股票查询助手，以下是关于股票历史价格表的字段信息，我可能会编写对应的SQL，对数据进行查询

-- 股票历史价格表：stock_history
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
);

可用的股票包括：
- 贵州茅台 (600519.SH)
- 五粮液 (000858.SZ)
- 广发证券 (000776.SZ)
- 中芯国际 (688981.SH)

数据时间范围：2020-01-01 至今

重要注意事项：
1. 表名：stock_history（不是 stock_daily）
2. 字段名：使用中文字段名，如 股票名称、交易日期、收盘价、涨跌幅 等（不要使用 stock_name、trade_date、close）
3. 交易日期格式：YYYYMMDD，例如 '20250102'、'20250103'

SQL查询示例：
- 查询2025年贵州茅台的收盘价：SELECT 交易日期, 收盘价 FROM stock_history WHERE 股票名称 = '贵州茅台' AND 交易日期 >= '20250101' AND 交易日期 <= '20251231' ORDER BY 交易日期
- 查询2025年所有股票数据：SELECT * FROM stock_history WHERE 交易日期 >= '20250101' AND 交易日期 <= '20251231'
- 对比多只股票的涨跌幅：SELECT 股票名称, 交易日期, 涨跌幅, 收盘价 FROM stock_history WHERE 股票名称 IN ('贵州茅台', '中芯国际') AND 交易日期 >= '20250101' AND 交易日期 <= '20251231' ORDER BY 股票名称, 交易日期

涨跌幅计算说明：
- 表中已有 涨跌幅 字段，可以直接使用
- 如需自行计算：涨跌幅 = (收盘价 - 昨收价) / 昨收价 * 100%
- 全年涨跌幅：(最后一天收盘价 - 第一天收盘价) / 第一天收盘价 * 100%

ARIMA预测功能说明：
- 当用户询问股票未来价格预测、走势预测时，必须使用 arima_stock 工具
- 不要自己尝试编写ARIMA代码或解释ARIMA理论，直接调用工具即可
- 工具名称：arima_stock
- 参数说明：
  * ts_code：股票代码（必填），例如 '600519.SH' 表示贵州茅台，'000858.SZ' 表示五粮液，'688981.SH' 表示中芯国际，'000776.SZ' 表示广发证券
  * n：预测天数（可选，默认5天）
- 调用示例：
  * 预测贵州茅台未来10天：arima_stock(ts_code='600519.SH', n=10)
  * 预测五粮液未来7天：arima_stock(ts_code='000858.SZ', n=7)
  * 预测中芯国际未来5天：arima_stock(ts_code='688981.SH')

布林带异常检测功能说明：
- 当用户询问股票异常点、超买超卖、价格异常时，必须使用 boll_detection 工具
- 不要自己尝试编写布林带代码或解释布林带理论，直接调用工具即可
- 工具名称：boll_detection
- 参数说明：
  * ts_code：股票代码或名称（必填），例如 '600519.SH' 或 '贵州茅台'
  * start_date：开始日期（可选，默认一年前），格式 YYYYMMDD
  * end_date：结束日期（可选，默认今天），格式 YYYYMMDD
- 布林带原理：
  * 中轨：20日移动平均线
  * 上轨：中轨 + 2倍标准差
  * 下轨：中轨 - 2倍标准差
  * 超买信号：收盘价突破上轨
  * 超卖信号：收盘价跌破下轨
- 调用示例：
  * 检测贵州茅台过去1年的异常：boll_detection(ts_code='600519.SH')
  * 检测2025年1月的异常：boll_detection(ts_code='贵州茅台', start_date='20250101', end_date='20250131')

qwen3.6-35b-a3bqwen3.6-35b-a3b实时查询功能说明：
- 当用户询问股票最新价格、今日行情、实时数据时，必须使用 get_stock_realtime 工具
- 不要自己尝试编写Tushare代码或解释API，直接调用工具即可
- 工具名称：get_stock_realtime
- 参数说明：
  * ts_code：股票代码或名称（必填），例如 '600519.SH' 或 '贵州茅台'
- 调用示例：
  * 查询贵州茅台实时行情：get_stock_realtime(ts_code='600519.SH')
  * 查询五粮液今日行情：get_stock_realtime(ts_code='五粮液')

注意事项：
- 用户问"预测茅台未来..."时，直接调用 arima_stock 工具
- 用户问"茅台异常点"、"茅台超买超卖"时，直接调用 boll_detection 工具
- 用户问"茅台最新价格"、"茅台今日行情"、"茅台实时数据"时，直接调用 get_stock_realtime 工具
- 不要解释技术原理，直接调用工具

我将回答用户关于股票历史价格相关的问题，例如：
- 某只股票在某个时间段的走势
- 多只股票的价格对比
- 股票的涨跌幅统计
- 成交量分析等
- 股票价格预测
- 股票异常点检测（超买超卖）

每当工具返回 markdown 表格和图片时，你必须原样输出工具返回的全部内容（包括图片 markdown），不要只总结表格，也不要省略图片。这样用户才能直接看到表格和图片。
"""

functions_desc = [
    {
        "name": "exc_sql",
        "description": "对于生成的SQL，进行SQL查询",
        "parameters": {
            "type": "object",
            "properties": {
                "sql_input": {
                    "type": "string",
                    "description": "生成的SQL语句",
                }
            },
            "required": ["sql_input"],
        },
    },
    {
        "name": "arima_stock",
        "description": "使用ARIMA模型预测股票未来N天的收盘价，支持股票代码(如600519.SH)或股票名称(如贵州茅台)",
        "parameters": {
            "type": "object",
            "properties": {
                "ts_code": {
                    "type": "string",
                    "description": "股票代码或股票名称，如 '600519.SH' 或 '贵州茅台'",
                },
                "n": {
                    "type": "integer",
                    "description": "预测天数，默认5天",
                }
            },
            "required": ["ts_code"],
        },
    },
    {
        "name": "boll_detection",
        "description": "使用布林带检测股票的超买超卖异常点，支持股票代码或股票名称",
        "parameters": {
            "type": "object",
            "properties": {
                "ts_code": {
                    "type": "string",
                    "description": "股票代码或股票名称，如 '600519.SH' 或 '贵州茅台'",
                },
                "start_date": {
                    "type": "string",
                    "description": "开始日期，格式YYYYMMDD，默认一年前",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式YYYYMMDD，默认今天",
                }
            },
            "required": ["ts_code"],
        },
    },
    {
        "name": "get_stock_realtime",
        "description": "通过Tushare API获取股票实时行情数据，支持股票代码(如600519.SH)或股票名称(如贵州茅台)",
        "parameters": {
            "type": "object",
            "properties": {
                "ts_code": {
                    "type": "string",
                    "description": "股票代码或股票名称，如 '600519.SH' 或 '贵州茅台'",
                }
            },
            "required": ["ts_code"],
        },
    },
]

_last_df_dict = {}

STOCK_NAME_TO_CODE = {
    '贵州茅台': '600519.SH',
    '五粮液': '000858.SZ',
    '广发证券': '000776.SZ',
    '中芯国际': '688981.SH',
}

CODE_TO_NAME = {v: k for k, v in STOCK_NAME_TO_CODE.items()}

def get_session_id(kwargs):
    """根据 kwargs 获取当前会话的唯一 session_id"""
    messages = kwargs.get('messages')
    if messages is not None:
        return id(messages)
    return None


def resolve_stock_code(ts_code):
    """将股票名称或代码统一解析为 (actual_code, stock_name)"""
    if ts_code in STOCK_NAME_TO_CODE:
        return STOCK_NAME_TO_CODE[ts_code], ts_code
    elif ts_code in CODE_TO_NAME:
        return ts_code, CODE_TO_NAME[ts_code]
    return ts_code, ts_code


def fetch_real_stock_name(actual_code):
    """通过 Tushare stock_basic 接口查询股票的真实名称"""
    try:
        import tushare as ts
        token = os.getenv('TUSHARE_TOKEN')
        if not token:
            return actual_code
        ts.set_token(token)
        pro = ts.pro_api()
        info = pro.stock_basic(ts_code=actual_code, fields='ts_code,name')
        if info is not None and not info.empty:
            return info['name'].iloc[0]
    except Exception as e:
        print(f'[WARN] 查询股票名称失败: {e}')
    return actual_code


def fetch_and_store_stock_data(actual_code, stock_name, start_date, end_date):
    """通过 Tushare 拉取股票历史数据并写入 SQLite，返回拉取的记录数。
    如果 Tushare 不可用（未配置 token 等），返回 0。"""
    try:
        import tushare as ts
        token = os.getenv('TUSHARE_TOKEN')
        if not token:
            print(f'[WARN] TUSHARE_TOKEN 未配置，无法拉取 {stock_name}({actual_code}) 的数据')
            return 0

        ts.set_token(token)
        pro = ts.pro_api()

        real_name = fetch_real_stock_name(actual_code)
        if real_name != stock_name:
            print(f'[INFO] 股票名称修正: {stock_name} -> {real_name}')
            stock_name = real_name

        df = pro.daily(ts_code=actual_code, start_date=start_date, end_date=end_date)
        if df.empty:
            print(f'[WARN] Tushare 返回空数据: {stock_name}({actual_code}) {start_date}~{end_date}')
            return 0

        df = df[['trade_date', 'open', 'high', 'low', 'close', 'pre_close', 'change', 'pct_chg', 'vol', 'amount']].copy()
        df.columns = ['交易日期', '开盘价', '最高价', '最低价', '收盘价', '昨收价', '涨跌额', '涨跌幅', '成交量', '成交额']
        df['股票名称'] = stock_name
        df['股票代码'] = actual_code
        df = df[['交易日期', '股票名称', '股票代码', '开盘价', '最高价', '最低价', '收盘价', '昨收价', '涨跌额', '涨跌幅', '成交量', '成交额']]

        db_path = os.path.join(os.path.dirname(__file__), 'stock_history.db')
        conn = sqlite3.connect(db_path)
        try:
            df.to_sql('stock_history', conn, if_exists='append', index=False)
            count = len(df)
            print(f'[INFO] 已从 Tushare 拉取并写入 {count} 条 {stock_name}({actual_code}) 数据')
            return count
        finally:
            conn.close()
    except Exception as e:
        print(f'[ERROR] fetch_and_store_stock_data 失败: {e}')
        return 0

@register_tool('exc_sql')
class ExcSQLTool(BaseTool):
    """
    SQL查询工具，执行传入的SQL语句并返回结果，并自动进行可视化。
    注意：当查询结果只有1行数据时，不进行可视化，只返回表格。
    """
    description = '对于生成的SQL，进行SQL查询，并自动可视化'
    parameters = [{
        'name': 'sql_input',
        'type': 'string',
        'description': '生成的SQL语句',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        import json
        import matplotlib.pyplot as plt
        import io, os, time
        import numpy as np
        from sqlalchemy import text

        session_id = get_session_id(kwargs)

        args = json.loads(params)
        sql_input = args['sql_input']
        print('sql_input=', sql_input)

        db_path = os.path.join(os.path.dirname(__file__), 'stock_history.db')
        engine = create_engine(f'sqlite:///{db_path}')
        
        df = pd.read_sql(text(sql_input), engine)
        print('df=', df)

        if session_id:
            _last_df_dict[session_id] = df

        stock_col = None
        for col in df.columns:
            if '股票' in col and '名称' in col:
                stock_col = col
                break
        
        if stock_col is not None and df[stock_col].nunique() > 1:
            md_parts = []
            for stock_name in df[stock_col].unique():
                stock_df = df[df[stock_col] == stock_name]
                md_parts.append(f"**股票：{stock_name}**")
                
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
        
        save_dir = os.path.join(os.path.dirname(__file__), 'image_show')
        os.makedirs(save_dir, exist_ok=True)
        filename = f'chart_{int(time.time() * 1000)}.png'
        save_path = os.path.join(save_dir, filename)
        
        generate_chart_png(df, save_path)
        
        img_md = f'![图表]({save_path})'
        return f"{md}\n\n{img_md}"


@register_tool('arima_stock')
class ArimaStockTool(BaseTool):
    """
    ARIMA股票预测工具，使用ARIMA(5,1,5)模型预测未来N天的收盘价。
    支持通过股票代码或股票名称进行预测。
    """
    description = '使用ARIMA模型预测股票未来N天的收盘价，支持股票代码(如600519.SH)或股票名称(如贵州茅台)'
    parameters = [{
        'name': 'ts_code',
        'type': 'string',
        'description': '股票代码或股票名称，如 600519.SH 或 贵州茅台',
        'required': True
    }, {
        'name': 'n',
        'type': 'integer',
        'description': '预测天数，默认5天',
        'required': False
    }]

    def call(self, params: str, **kwargs) -> str:
        import json
        import traceback
        import warnings
        from statsmodels.tsa.arima.model import ARIMA
        
        warnings.filterwarnings('ignore')
        
        try:
            args = json.loads(params)
            ts_code = args['ts_code']
            n = args.get('n', 5)
            
            if n < 1 or n > 365:
                return f"错误：预测天数必须在1-365天之间，当前值为{n}"
            
            print(f'[DEBUG] arima_stock: ts_code={ts_code}, n={n}')

            actual_code, stock_name = resolve_stock_code(ts_code)
            print(f'[DEBUG] 解析后: stock_name={stock_name}, actual_code={actual_code}')

            db_path = os.path.join(os.path.dirname(__file__), 'stock_history.db')
            engine = create_engine(f'sqlite:///{db_path}')

            today = datetime.now()
            one_year_ago = today - timedelta(days=365)
            start_date = one_year_ago.strftime('%Y%m%d')
            end_date = today.strftime('%Y%m%d')

            print(f'[DEBUG] 查询日期范围: {start_date} 至今')

            query = f"""
            SELECT 交易日期, 收盘价
            FROM stock_history
            WHERE 股票代码 = '{actual_code}'
            AND 交易日期 >= '{start_date}'
            ORDER BY 交易日期
            """

            print(f'[DEBUG] SQL: {query}')

            df = pd.read_sql(text(query), engine)
            print(f'[DEBUG] 查询结果: {len(df)}条记录')

            if len(df) == 0:
                print(f'[INFO] 数据库中无 {stock_name}({actual_code}) 数据，尝试从 Tushare 拉取...')
                fetched = fetch_and_store_stock_data(actual_code, stock_name, start_date, end_date)
                if fetched > 0:
                    print(f'[INFO] 拉取成功({fetched}条)，重新查询数据库...')
                    df = pd.read_sql(text(query), engine)
                if len(df) == 0:
                    return f"无法找到股票 {stock_name}({actual_code}) 的历史数据。\n" \
                           f"可能原因：\n1. 股票代码不正确\n2. TUSHARE_TOKEN 未配置或额度不足\n3. 该股票无历史数据\n" \
                           f"请设置环境变量 TUSHARE_TOKEN 后重试。"
            
            if len(df) < 30:
                return f"股票 {stock_name} 的历史数据不足30条（当前仅{len(df)}条），无法进行ARIMA预测。建议：\n1. 增加数据时间范围\n2. 使用更多历史数据"
            
            df_clean = df.dropna(subset=['收盘价']).copy()
            df_clean['收盘价'] = df_clean['收盘价'].replace([np.inf, -np.inf], np.nan).dropna()
            
            if len(df_clean) < 30:
                return f"股票 {stock_name} 的有效数据不足30条（原始{len(df)}条，有效{len(df_clean)}条），无法进行ARIMA预测。数据可能存在缺失或异常值。"
            
            prices = df_clean['收盘价'].values.astype(float)
            
            if np.std(prices) < 1e-10:
                return f"股票 {stock_name} 的价格数据无波动（所有价格相同），无法进行ARIMA预测。"
            
            print(f'[DEBUG] 开始ARIMA建模: order=(5,1,5), 数据量={len(prices)}')
            print(f'[DEBUG] 价格范围: {prices.min():.2f} ~ {prices.max():.2f}, 均值={np.mean(prices):.2f}')
            
            try:
                model = ARIMA(prices, order=(5, 1, 5))
                model_fit = model.fit()
            except Exception as e:
                print(f'[ERROR] ARIMA建模失败: {str(e)}')
                print(f'[DEBUG] 尝试简化模型: order=(2,1,2)')
                try:
                    model = ARIMA(prices, order=(2, 1, 2))
                    model_fit = model.fit()
                except Exception as e2:
                    return f"ARIMA模型的拟合失败：{str(e2)}\n\n这可能是由于数据波动模式不适合ARIMA模型。建议：\n1. 检查数据是否连续\n2. 使用其他预测方法（如移动平均）"
            
            print(f'[DEBUG] ARIMA模型拟合完成')
            print(f'[DEBUG] AIC: {model_fit.aic:.2f}')
            
            forecast_result = model_fit.get_forecast(steps=n)
            forecast = forecast_result.predicted_mean
            conf_int = forecast_result.conf_int(alpha=0.05)
            
            if hasattr(conf_int, 'iloc'):
                conf_lower = conf_int.iloc[:, 0]
                conf_upper = conf_int.iloc[:, 1]
            else:
                conf_lower = conf_int[:, 0]
                conf_upper = conf_int[:, 1]
            
            last_date_str = df_clean['交易日期'].iloc[-1]
            last_date = datetime.strptime(last_date_str, '%Y%m%d')
            
            forecast_dates = []
            for i in range(1, n + 1):
                next_date = last_date + timedelta(days=i)
                forecast_dates.append(next_date.strftime('%Y%m%d'))
            
            forecast_df = pd.DataFrame({
                '预测日期': forecast_dates,
                '预测收盘价': forecast,
                '置信区间下限': conf_lower,
                '置信区间上限': conf_upper
            })
            
            md = forecast_df.to_markdown(index=False)
            
            save_dir = os.path.join(os.path.dirname(__file__), 'image_show')
            os.makedirs(save_dir, exist_ok=True)
            filename = f'arima_{int(time.time() * 1000)}.png'
            save_path = os.path.join(save_dir, filename)
            
            fig, ax = plt.subplots(figsize=(14, 7))
            
            hist_len = min(60, len(df_clean))
            hist_dates = df_clean['交易日期'].tail(hist_len).values
            hist_prices = df_clean['收盘价'].tail(hist_len).values
            
            ax.plot(range(hist_len), hist_prices, label='历史收盘价', linewidth=2.5, color='#1f77b4', marker='o', markersize=3)
            
            forecast_indices = range(hist_len, hist_len + n)
            
            ax.fill_between(forecast_indices, conf_lower, conf_upper, 
                            color='#ff7f0e', alpha=0.2, label='95%置信区间')
            
            ax.plot(forecast_indices, forecast, 
                    label='预测收盘价', linewidth=2.5, color='#ff7f0e', marker='s', markersize=6)
            
            ax.plot([hist_len - 1, hist_len], [hist_prices[-1], forecast[0]], 
                    color='#2ca02c', linewidth=2, linestyle='--', marker='D', markersize=8)
            
            ax.scatter([hist_len - 1], [hist_prices[-1]], color='#1f77b4', s=100, zorder=5, edgecolors='black', linewidths=1.5)
            ax.annotate(f'{hist_prices[-1]:.2f}', (hist_len - 1, hist_prices[-1]), 
                        textcoords="offset points", xytext=(0, 10), ha='center', fontsize=10, color='#1f77b4')
            
            for i in [0, n-1]:
                ax.scatter([hist_len + i], [forecast[i]], color='#ff7f0e', s=80, zorder=5, edgecolors='black', linewidths=1.5)
                ax.annotate(f'{forecast[i]:.2f}', (hist_len + i, forecast[i]), 
                            textcoords="offset points", xytext=(0, 10), ha='center', fontsize=10, color='#ff7f0e')
            
            ax.axvline(x=hist_len - 0.5, color='green', linestyle='--', linewidth=1.5, alpha=0.7)
            ax.axvspan(hist_len - 0.5, hist_len + n - 0.5, alpha=0.1, color='green', label='预测区间')
            
            all_dates = list(hist_dates) + forecast_dates
            total_len = len(all_dates)
            sample_count = min(12, total_len)
            sample_indices = np.linspace(0, total_len - 1, sample_count, dtype=int)
            sample_labels = [str(all_dates[i]) for i in sample_indices]
            
            ax.set_xticks(sample_indices)
            ax.set_xticklabels(sample_labels, rotation=45, ha='right', fontsize=9)
            
            ax.legend(loc='upper left', fontsize=10)
            ax.set_title(f'ARIMA(5,1,5)预测 - {stock_name}({actual_code}) 未来{n}天收盘价', fontsize=14, fontweight='bold')
            ax.set_xlabel('日期', fontsize=11)
            ax.set_ylabel('收盘价（元）', fontsize=11)
            ax.grid(True, alpha=0.3, linestyle='--')
            
            min_val = min(min(hist_prices), min(conf_lower))
            max_val = max(max(hist_prices), max(conf_upper))
            margin = (max_val - min_val) * 0.1
            ax.set_ylim(min_val - margin, max_val + margin)
            
            plt.tight_layout()
            plt.savefig(save_path, dpi=120)
            plt.close()
            
            last_price = prices[-1]
            avg_forecast = np.mean(forecast)
            change_pct = (avg_forecast - last_price) / last_price * 100
            
            min_forecast = min(forecast)
            max_forecast = max(forecast)
            min_conf = min(conf_lower)
            max_conf = max(conf_upper)
            
            summary = f"""
**预测摘要：**
- 股票名称：{stock_name}
- 股票代码：{actual_code}
- 当前收盘价：{last_price:.2f}
- 预测{n}天平均价格：{avg_forecast:.2f}
- 预测最高价：{max_forecast:.2f}
- 预测最低价：{min_forecast:.2f}
- 预测变化幅度：{change_pct:.2f}%
- 95%置信区间范围：{min_conf:.2f} ~ {max_conf:.2f}
- 使用数据：过去一年 ({len(df_clean)}条有效数据)
- 模型：ARIMA(5,1,5)
"""
            
            img_md = f'![预测图表]({save_path})'
            
            return f"{summary}\n\n**预测详情：**\n{md}\n\n{img_md}"
            
        except Exception as e:
            import traceback
            print(f'[ERROR] arima_stock异常: {str(e)}')
            print(traceback.format_exc())
            return f"预测过程中出现错误：{str(e)}\n\n请检查：\n1. 股票代码是否正确\n2. 是否有足够的历史数据\n3. 是否已安装statsmodels库"


@register_tool('get_stock_realtime')
class GetStockRealtimeTool(BaseTool):
    """
    实时股票数据查询工具，通过Tushare API获取实时行情数据。
    """
    description = '通过Tushare API获取股票实时行情数据，支持股票代码或股票名称'
    parameters = [{
        'name': 'ts_code',
        'type': 'string',
        'description': '股票代码或股票名称，如 600519.SH 或 贵州茅台',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        import json
        
        try:
            args = json.loads(params)
            ts_code = args['ts_code']
            
            stock_name_to_code = {
                '贵州茅台': '600519.SH',
                '五粮液': '000858.SZ',
                '广发证券': '000776.SZ',
                '中芯国际': '688981.SH',
            }
            
            code_to_name = {
                '600519.SH': '贵州茅台',
                '000858.SZ': '五粮液',
                '000776.SZ': '广发证券',
                '688981.SH': '中芯国际',
            }
            
            actual_code = ts_code
            stock_name = ts_code
            if ts_code in stock_name_to_code:
                actual_code = stock_name_to_code[ts_code]
                stock_name = ts_code
            elif ts_code in code_to_name:
                actual_code = ts_code
                stock_name = code_to_name[ts_code]
            
            print(f'[DEBUG] get_stock_realtime: ts_code={ts_code}, actual_code={actual_code}')
            
            import tushare as ts
            
            token = os.getenv('TUSHARE_TOKEN')
            if not token:
                return "错误：未设置TUSHARE_TOKEN环境变量\n\n请设置环境变量后重试：\n  Windows: set TUSHARE_TOKEN=你的token\n  Linux/Mac: export TUSHARE_TOKEN=你的token"
            
            ts.set_token(token)
            pro = ts.pro_api()
            
            df = pro.daily(ts_code=actual_code, start_date=datetime.now().strftime('%Y%m%d'), end_date=datetime.now().strftime('%Y%m%d'))
            
            if df.empty:
                return f"无法获取股票 {stock_name} 的实时数据。可能原因：\n1. 当前非交易日\n2. Tushare token 失效\n3. 股票代码错误"
            
            df['股票名称'] = stock_name
            df = df[['trade_date', '股票名称', 'ts_code', 'open', 'high', 'low', 'close', 'pre_close', 'change', 'pct_chg', 'vol', 'amount']]
            df.columns = ['交易日期', '股票名称', '股票代码', '开盘价', '最高价', '最低价', '收盘价', '昨收价', '涨跌额', '涨跌幅(%)', '成交量(手)', '成交额(千元)']
            
            md = df.to_markdown(index=False)
            
            save_dir = os.path.join(os.path.dirname(__file__), 'image_show')
            os.makedirs(save_dir, exist_ok=True)
            filename = f'realtime_{int(time.time() * 1000)}.png'
            save_path = os.path.join(save_dir, filename)
            
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.bar(['开盘价', '最高价', '最低价', '收盘价'], 
                   [df['开盘价'].iloc[0], df['最高价'].iloc[0], df['最低价'].iloc[0], df['收盘价'].iloc[0]],
                   color=['#1f77b4', '#2ca02c', '#d62728', '#ff7f0e'])
            
            for i, v in enumerate([df['开盘价'].iloc[0], df['最高价'].iloc[0], df['最低价'].iloc[0], df['收盘价'].iloc[0]]):
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


@register_tool('boll_detection')
class BollDetectionTool(BaseTool):
    """
    布林带异常检测工具，使用20日周期+2σ进行超买超卖检测。
    """
    description = '使用布林带(20日+2σ)检测股票的超买超卖异常点'
    parameters = [{
        'name': 'ts_code',
        'type': 'string',
        'description': '股票代码或股票名称，如 600519.SH 或 贵州茅台',
        'required': True
    }, {
        'name': 'start_date',
        'type': 'string',
        'description': '开始日期，格式YYYYMMDD，默认一年前',
        'required': False
    }, {
        'name': 'end_date',
        'type': 'string',
        'description': '结束日期，格式YYYYMMDD，默认今天',
        'required': False
    }]

    def call(self, params: str, **kwargs) -> str:
        import json
        import traceback
        
        try:
            args = json.loads(params)
            ts_code = args['ts_code']
            start_date = args.get('start_date')
            end_date = args.get('end_date')
            
            print(f'[DEBUG] boll_detection: ts_code={ts_code}, start_date={start_date}, end_date={end_date}')

            actual_code, stock_name = resolve_stock_code(ts_code)

            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')

            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')

            print(f'[DEBUG] 解析后: stock_name={stock_name}, actual_code={actual_code}')
            print(f'[DEBUG] 日期范围: {start_date} ~ {end_date}')

            db_path = os.path.join(os.path.dirname(__file__), 'stock_history.db')
            engine = create_engine(f'sqlite:///{db_path}')

            query = f"""
            SELECT 交易日期, 收盘价, 最高价, 最低价
            FROM stock_history
            WHERE 股票代码 = '{actual_code}'
            AND 交易日期 >= '{start_date}'
            AND 交易日期 <= '{end_date}'
            ORDER BY 交易日期
            """

            print(f'[DEBUG] SQL: {query}')

            df = pd.read_sql(text(query), engine)
            print(f'[DEBUG] 查询结果: {len(df)}条记录')

            if len(df) == 0:
                print(f'[INFO] 数据库中无 {stock_name}({actual_code}) 数据，尝试从 Tushare 拉取...')
                fetched = fetch_and_store_stock_data(actual_code, stock_name, start_date, end_date)
                if fetched > 0:
                    print(f'[INFO] 拉取成功({fetched}条)，重新查询数据库...')
                    df = pd.read_sql(text(query), engine)
                if len(df) == 0:
                    return f"无法找到股票 {stock_name}({actual_code}) 在 {start_date} ~ {end_date} 的历史数据。\n" \
                           f"可能原因：\n1. 股票代码不正确\n2. TUSHARE_TOKEN 未配置或额度不足\n3. 该股票无历史数据\n" \
                           f"请设置环境变量 TUSHARE_TOKEN 后重试。"
            
            if len(df) < 20:
                return f"股票 {stock_name} 的数据不足20条，无法计算布林带"
            
            df['收盘价'] = df['收盘价'].astype(float)
            
            period = 20
            std_dev = 2
            
            df['MA'] = df['收盘价'].rolling(window=period).mean()
            df['STD'] = df['收盘价'].rolling(window=period).std()
            df['Upper'] = df['MA'] + std_dev * df['STD']
            df['Lower'] = df['MA'] - std_dev * df['STD']
            
            df['超买'] = df['收盘价'] > df['Upper']
            df['超卖'] = df['收盘价'] < df['Lower']
            
            overbought = df[df['超买']].copy()
            oversold = df[df['超卖']].copy()
            
            print(f'[DEBUG] 超买点数: {len(overbought)}, 超卖点数: {len(oversold)}')
            
            if len(overbought) > 0:
                overbought_display = overbought[['交易日期', '收盘价', 'Upper']].head(20)
                overbought_display['突破幅度'] = (overbought_display['收盘价'] - overbought_display['Upper']) / overbought_display['Upper'] * 100
                overbought_md = overbought_display.to_markdown(index=False, floatfmt='.2f')
            else:
                overbought_md = "无超买信号"
            
            if len(oversold) > 0:
                oversold_display = oversold[['交易日期', '收盘价', 'Lower']].head(20)
                oversold_display['跌破幅度'] = (oversold_display['Lower'] - oversold_display['收盘价']) / oversold_display['Lower'] * 100
                oversold_md = oversold_display.to_markdown(index=False, floatfmt='.2f')
            else:
                oversold_md = "无超卖信号"
            
            save_dir = os.path.join(os.path.dirname(__file__), 'image_show')
            os.makedirs(save_dir, exist_ok=True)
            filename = f'boll_{int(time.time() * 1000)}.png'
            save_path = os.path.join(save_dir, filename)
            
            fig, ax = plt.subplots(figsize=(16, 8))
            
            ax.plot(df['交易日期'], df['收盘价'], label='收盘价', linewidth=2, color='#1f77b4', alpha=0.8)
            ax.plot(df['交易日期'], df['MA'], label='中轨(MA20)', linewidth=1.5, color='#ff7f0e', linestyle='-')
            ax.plot(df['交易日期'], df['Upper'], label='上轨(+2σ)', linewidth=1.5, color='#d62728', linestyle='-')
            ax.plot(df['交易日期'], df['Lower'], label='下轨(-2σ)', linewidth=1.5, color='#2ca02c', linestyle='-')
            
            ax.fill_between(df['交易日期'], df['Upper'], df['Lower'], alpha=0.1, color='#ff7f0e', label='布林带区域')
            
            if len(overbought) > 0:
                ax.scatter(overbought['交易日期'], overbought['收盘价'], 
                          color='#d62728', s=100, marker='^', label='超买信号', zorder=5, edgecolors='black', linewidths=1)
            
            if len(oversold) > 0:
                ax.scatter(oversold['交易日期'], oversold['收盘价'], 
                          color='#2ca02c', s=100, marker='v', label='超卖信号', zorder=5, edgecolors='black', linewidths=1)
            
            total_len = len(df)
            sample_count = min(15, total_len)
            sample_indices = np.linspace(0, total_len - 1, sample_count, dtype=int)
            sample_labels = [str(df['交易日期'].iloc[i]) for i in sample_indices]
            
            ax.set_xticks(sample_indices)
            ax.set_xticklabels(sample_labels, rotation=45, ha='right', fontsize=9)
            
            ax.legend(loc='upper left', fontsize=10)
            ax.set_title(f'布林带异常检测 - {stock_name}({actual_code})\n{start_date} ~ {end_date}', fontsize=14, fontweight='bold')
            ax.set_xlabel('日期', fontsize=11)
            ax.set_ylabel('价格（元）', fontsize=11)
            ax.grid(True, alpha=0.3, linestyle='--')
            
            plt.tight_layout()
            plt.savefig(save_path, dpi=120)
            plt.close()
            
            latest_price = df['收盘价'].iloc[-1]
            latest_upper = df['Upper'].iloc[-1]
            latest_lower = df['Lower'].iloc[-1]
            latest_ma = df['MA'].iloc[-1]
            
            latest_status = "正常区间"
            if latest_price > latest_upper:
                latest_status = "超买"
            elif latest_price < latest_lower:
                latest_status = "超卖"
            
            summary = f"""
**布林带检测摘要：**
- 股票名称：{stock_name}
- 股票代码：{actual_code}
- 检测时间范围：{start_date} ~ {end_date}
- 布林带参数：{period}日周期 + {std_dev}σ
- 总检测数据：{len(df)}条
- 超买信号数：{len(overbought)}次
- 超卖信号数：{len(oversold)}次
- 当前状态：{latest_status}
- 当前收盘价：{latest_price:.2f}
- 当前中轨：{latest_ma:.2f}
- 当前上轨：{latest_upper:.2f}
- 当前下轨：{latest_lower:.2f}
"""
            
            img_md = f'![布林带图表]({save_path})'
            
            return f"{summary}\n\n**超买信号（收盘价突破上轨）：**\n{overbought_md}\n\n**超卖信号（收盘价跌破下轨）：**\n{oversold_md}\n\n{img_md}"
            
        except Exception as e:
            import traceback
            print(f'[ERROR] boll_detection异常: {str(e)}')
            print(traceback.format_exc())
            return f"布林带检测过程中出现错误：{str(e)}\n\n请检查：\n1. 股票代码是否正确\n2. 日期格式是否为YYYYMMDD\n3. 是否有足够的历史数据（至少20条）"


def generate_chart_png(df_sql, save_path):
    """
    根据数据量自动选择图表类型：
    - 数据量 <= 20 条：使用柱状图
    - 数据量 > 20 条：使用折线图，并对横坐标进行采样（最多显示10个点）
    """
    columns = df_sql.columns
    data_len = len(df_sql)
    
    object_columns = df_sql.select_dtypes(include='O').columns.tolist()
    if columns[0] in object_columns:
        object_columns.remove(columns[0])
    
    num_columns = df_sql.select_dtypes(exclude='O').columns.tolist()
    
    use_line_chart = data_len > 20
    
    if data_len > 20:
        sample_indices = np.linspace(0, data_len - 1, 10, dtype=int)
        sample_labels = [str(df_sql[columns[0]].iloc[i]) for i in sample_indices]
    else:
        sample_indices = np.arange(data_len)
        sample_labels = [str(df_sql[columns[0]].iloc[i]) for i in sample_indices]
    
    if len(object_columns) > 0:
        pivot_df = df_sql.pivot_table(index=columns[0], columns=object_columns, 
                                      values=num_columns, 
                                      fill_value=0)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if use_line_chart:
            for col in pivot_df.columns:
                label_str = str(col)
                safe_label = label_str.replace('%', '%%').replace('{', '{{').replace('}', '}}')
                ax.plot(pivot_df.index, pivot_df[col], marker='o', markersize=4, label=safe_label, linewidth=2)
        else:
            bottoms = None
            for col in pivot_df.columns:
                label_str = str(col)
                safe_label = label_str.replace('%', '%%').replace('{', '{{').replace('}', '}}')
                ax.bar(pivot_df.index, pivot_df[col], bottom=bottoms, label=safe_label)
                if bottoms is None:
                    bottoms = pivot_df[col].copy()
                else:
                    bottoms += pivot_df[col]
    else:
        x = np.arange(data_len)
        
        if use_line_chart:
            fig, ax = plt.subplots(figsize=(10, 6))
            for column in columns[1:]:
                label_str = str(column)
                safe_label = label_str.replace('%', '%%').replace('{', '{{').replace('}', '}}')
                ax.plot(x, df_sql[column], marker='o', markersize=4, label=safe_label, linewidth=2)
            
            ax.set_xticks(sample_indices)
            safe_sample_labels = [l.replace('%', '%%').replace('{', '{{').replace('}', '}}') for l in sample_labels]
            ax.set_xticklabels(safe_sample_labels, rotation=45, ha='right')
        else:
            bottom = np.zeros(data_len)
            for column in columns[1:]:
                label_str = str(column)
                safe_label = label_str.replace('%', '%%').replace('{', '{{').replace('}', '}}')
                plt.bar(x, df_sql[column], bottom=bottom, label=safe_label)
                bottom += df_sql[column]
            
            safe_xtick_labels = []
            for val in df_sql[columns[0]]:
                val_str = str(val)
                safe_val = val_str.replace('%', '%%').replace('{', '{{').replace('}', '}}')
                safe_xtick_labels.append(safe_val)
            plt.xticks(x, safe_xtick_labels)
    
    plt.legend()
    chart_type = "折线图" if use_line_chart else "柱状图"
    plt.title(f"股票数据统计 ({chart_type}, {data_len}条数据)")
    
    xlabel_str = str(columns[0])
    safe_xlabel = xlabel_str.replace('%', '%%').replace('{', '{{').replace('}', '}}')
    plt.xlabel(safe_xlabel)
    plt.ylabel("数值")
    
    if not use_line_chart or len(object_columns) == 0:
        plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()


def init_agent_service():
    """初始化股票助手服务"""
    llm_cfg = {
        'model': 'qwen3.6-35b-a3b',
        'model_server': 'dashscope',
        'model_type': 'oai',
        'api_key': os.getenv('DASHSCOPE_API_KEY', ''),
        'timeout': 30,
        'retry_count': 3,
    }
    try:
        bot = Assistant(
            llm=llm_cfg,
            name='股票助手',
            description='股票查询与数据分析、预测、异常检测及实时行情',
            system_message=system_prompt,
            function_list=['exc_sql', 'arima_stock', 'boll_detection', 'get_stock_realtime', {
                "mcpServers": {
                    "tavily-mcp": {
                        "command": "npx",
                        "args": ["-y", "tavily-mcp@0.1.4"],
                        "env": {
                            "TAVILY_API_KEY": "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"
                        }
                    }
                }
            }],
            files=['faq.txt']
        )
        print("股票助手初始化成功！")
        return bot
    except Exception as e:
        print(f"股票助手初始化失败: {str(e)}")
        raise


def app_tui():
    """终端交互模式"""
    try:
        bot = init_agent_service()
        messages = []
        while True:
            try:
                query = input('user question: ')
                file = input('file url (press enter if no file): ').strip()
                
                if not query:
                    print('user question cannot be empty！')
                    continue
                    
                if not file:
                    messages.append({'role': 'user', 'content': query})
                else:
                    messages.append({'role': 'user', 'content': [{'text': query}, {'file': file}]})

                print("正在处理您的请求...")
                response = []
                for response in bot.run(messages):
                    print('bot response:', response)
                messages.extend(response)
            except Exception as e:
                print(f"处理请求时出错: {str(e)}")
                print("请重试或输入新的问题")
    except Exception as e:
        print(f"启动终端模式失败: {str(e)}")


def app_gui():
    """图形界面模式，提供 Web 图形界面"""
    try:
        print("正在启动 Web 界面...")
        bot = init_agent_service()
        chatbot_config = {
            'prompt.suggestions': [
                '贵州茅台2025年的收盘价走势如何？',
                '对比贵州茅台和五粮液2025年的收盘价',
                '预测贵州茅台未来10天的收盘价走势',
                '检测贵州茅台2025年的异常点',
                '检测中芯国际过去一年的超买超卖信号',
                '贵州茅台最新价格是多少？',
                '五粮液今日行情如何？',
            ]
        }
        print("Web 界面准备就绪，正在启动服务...")
        WebUI(
            bot,
            chatbot_config=chatbot_config
        ).run(share=False, server_name='0.0.0.0', server_port=7863, allowed_paths=[os.path.join(os.path.dirname(__file__), 'image_show')])
    except Exception as e:
        print(f"启动 Web 界面失败: {str(e)}")
        print("请检查网络连接和 API Key 配置")


if __name__ == '__main__':
    app_gui()