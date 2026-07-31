# -*- coding: utf-8 -*-
"""图表生成工具"""

from pathlib import Path
from typing import Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "SimSun", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False


def generate_chart_png(df: pd.DataFrame, save_path: Union[str, Path]) -> None:
    """根据 DataFrame 自动选择合适的图表类型并保存为 PNG"""
    record_count = len(df)

    # 判断是否有股票名称列（多股票对比场景）
    has_stock_col = any('股票' in col and '名称' in col for col in df.columns)

    if record_count <= 20:
        # 少量数据：柱状图
        _generate_bar_chart(df, save_path, has_stock_col)
    else:
        # 多条数据：折线图
        _generate_line_chart(df, save_path, has_stock_col)


def _generate_bar_chart(df: pd.DataFrame, save_path: Union[str, Path], has_stock_col: bool) -> None:
    """生成柱状图"""
    fig, ax = plt.subplots(figsize=(12, 6))

    # 找到数值列和标签列
    date_cols = [col for col in df.columns if '日期' in col]
    close_cols = [col for col in df.columns if '收盘' in col]
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if date_cols and close_cols:
        x_labels = df[date_cols[0]].astype(str)
        values = df[close_cols[0]]
        ax.bar(range(len(values)), values, color='#1f77b4', alpha=0.8)
        ax.set_xticks(range(len(x_labels)))
        ax.set_xticklabels(x_labels, rotation=45, ha='right', fontsize=8)
        ax.set_ylabel(close_cols[0])
        if has_stock_col:
            stock_col = [c for c in df.columns if '股票' in c and '名称' in c][0]
            ax.set_title(f"股票收盘价柱状图 - {df[stock_col].iloc[0]}")
        else:
            ax.set_title("收盘价柱状图")
    elif numeric_cols:
        values = df[numeric_cols[0]]
        ax.bar(range(len(values)), values, color='#1f77b4', alpha=0.8)
        ax.set_ylabel(numeric_cols[0])
        ax.set_title("数据柱状图")

    ax.grid(True, linestyle='--', alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=120, bbox_inches='tight')
    plt.close()


def _generate_line_chart(df: pd.DataFrame, save_path: Union[str, Path], has_stock_col: bool) -> None:
    """生成折线图"""
    fig, ax = plt.subplots(figsize=(14, 7))

    date_cols = [col for col in df.columns if '日期' in col]
    close_cols = [col for col in df.columns if '收盘' in col]
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if date_cols and close_cols:
        x_values = df[date_cols[0]].astype(str)
        y_values = df[close_cols[0]]
        ax.plot(range(len(y_values)), y_values, color='#1f77b4', linewidth=2, marker='')

        # 采样横坐标标签
        step = max(1, len(x_values) // 10)
        tick_indices = list(range(0, len(x_values), step))
        ax.set_xticks(tick_indices)
        ax.set_xticklabels([x_values.iloc[i] for i in tick_indices], rotation=45, ha='right', fontsize=8)
        ax.set_ylabel(close_cols[0])
        ax.set_title("收盘价走势图")
    elif numeric_cols:
        y_values = df[numeric_cols[0]]
        ax.plot(range(len(y_values)), y_values, color='#1f77b4', linewidth=2)
        step = max(1, len(y_values) // 10)
        tick_indices = list(range(0, len(y_values), step))
        ax.set_xticks(tick_indices)
        ax.set_ylabel(numeric_cols[0])
        ax.set_title("数据走势图")

    ax.grid(True, linestyle='--', alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=120, bbox_inches='tight')
    plt.close()
