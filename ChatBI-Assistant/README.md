# ChatBI-Assistant

基于大语言模型的智能量化分析助手，支持股票查询、技术指标分析、价格预测和实时行情查询。

## 项目结构

```
ChatBI-Assistant/
├── assistant_stock_bot.py        # 股票助手（主程序，完整版）
├── assistant_ticket_bot-3.py     # 门票订单助手
├── get_stock_data.py             # 从 Tushare 获取股票数据
├── get_stock_data_to_sqlite.py   # 数据导入 SQLite
├── init_stock_db.py              # 初始化数据库（含示例数据）
├── import_excel_to_db.py         # Excel 数据导入
├── check_db.py                   # 数据库检查工具
├── check_excel.py                # Excel 文件检查工具
├── faq.txt                       # 常见问题
├── stock_history.db              # SQLite 数据库
├── stock_history_data.xlsx       # 股票数据 Excel 备份
└── image_show/                   # 图表输出目录
```

## 核心功能

### 股票助手（assistant_stock_bot.py）

基于 Qwen Agent 框架，提供以下工具：

| 工具 | 功能 | 参数 |
|------|------|------|
| `exc_sql` | SQL 查询 + 自动可视化 | `sql_input`: SQL语句 |
| `arima_stock` | ARIMA 价格预测 | `ts_code`: 股票代码/名称, `n`: 预测天数 |
| `boll_detection` | 布林带异常检测 | `ts_code`: 股票代码/名称, `start_date`, `end_date` |
| `get_stock_realtime` | Tushare 实时行情 | `ts_code`: 股票代码/名称 |

**支持的股票**：
- 贵州茅台 (600519.SH)
- 五粮液 (000858.SZ)
- 广发证券 (000776.SZ)
- 中芯国际 (688981.SH)

**可视化特性**：
- 数据量 ≤ 20 条：柱状图
- 数据量 > 20 条：折线图（自动采样横坐标）
- 多股票数据：分组显示 + 对比图表
- ARIMA 预测：历史数据 + 预测曲线 + 95% 置信区间
- 布林带：中轨/上轨/下轨 + 超买超卖信号标记

### 门票订单助手（assistant_ticket_bot-3.py）

基于 MySQL 数据库的门票订单分析助手，支持：
- 一日票/二日票销量统计
- 按省份/渠道/时间分析
- 连接阿里云 MySQL 数据库

## 运行指南

### 环境要求

```bash
pip install qwen-agent dashscope pandas sqlalchemy matplotlib numpy statsmodels gradio tushare
```

### 配置

设置环境变量：

```bash
# Windows
set DASHSCOPE_API_KEY=你的API_KEY
set TUSHARE_TOKEN=你的TUSHARE_TOKEN

# Linux/Mac
export DASHSCOPE_API_KEY=你的API_KEY
export TUSHARE_TOKEN=你的TUSHARE_TOKEN
```

**Tushare Token 获取**：访问 https://tushare.pro/register 注册账号并获取 Token。

### 启动服务

```bash
# 股票助手 Web 界面（端口 7861）
python assistant_stock_bot.py

# 门票助手 Web 界面（端口 7860）
python assistant_ticket_bot-3.py
```

### 示例查询

```
- 贵州茅台2025年的收盘价走势如何？
- 对比贵州茅台和五粮液2025年的收盘价
- 预测贵州茅台未来10天的收盘价走势
- 检测贵州茅台2025年的异常点
- 检测中芯国际过去一年的超买超卖信号
- 贵州茅台最新价格是多少？
- 五粮液今日行情如何？
```

## 技术架构

### 核心组件

1. **Agent 框架**：Qwen Agent Assistant
2. **工具注册**：`@register_tool` 装饰器
3. **数据库**：SQLite（股票）、MySQL（门票）
4. **可视化**：Matplotlib
5. **前端**：Gradio WebUI

### 工具调用流程

```
用户提问 → LLM 分析 → 选择工具 → 执行工具 → 返回结果 → LLM 总结 → 用户
```

### 关键设计

- **会话隔离**：通过 `get_session_id()` + `_last_df_dict` 实现多用户数据隔离
- **自适应图表**：根据数据量自动选择图表类型
- **安全处理**：图表标签格式化安全（`%`、`{`、`}` 字符转义）
- **错误处理**：完善的异常捕获和用户友好提示

## 数据库结构

### stock_history 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| 交易日期 | TEXT | YYYYMMDD 格式 |
| 股票名称 | TEXT | 中文名称 |
| 股票代码 | TEXT | 如 600519.SH |
| 开盘价 | REAL | 开盘价格 |
| 最高价 | REAL | 最高价格 |
| 最低价 | REAL | 最低价格 |
| 收盘价 | REAL | 收盘价格 |
| 昨收价 | REAL | 昨日收盘 |
| 涨跌额 | REAL | 涨跌金额 |
| 涨跌幅 | REAL | 涨跌幅度（%） |
| 成交量 | REAL | 成交量 |
| 成交额 | REAL | 成交金额 |

## 数据获取

### 使用 Tushare

```bash
python get_stock_data.py
python get_stock_data_to_sqlite.py
```

需要配置 Tushare token（见 `get_stock_data.py` 第13行）。

### 使用初始化脚本

```bash
python init_stock_db.py
```

生成包含示例数据的 SQLite 数据库。

## 版本演进

```
v1 (assistant_stock_bot.py)
├── 基础SQL查询 + 固定柱状图
└── 简单可视化

v2 (assistant_stock_bot-2.py)
├── 智能图表选择（柱状图/折线图）
├── 多股票分组显示
├── 描述统计摘要
└── Tavily 搜索集成

v3 (assistant_stock_bot-3.py)
├── ARIMA 时间序列预测
├── 预测可视化（置信区间）
└── 预测摘要统计

v4 (assistant_stock_bot-4.py → assistant_stock_bot.py)
├── 布林带异常检测
├── 超买超卖信号分析
└── 完整功能集合
```

## 面试要点

### 技术亮点

1. **AI Agent 架构**：基于 Qwen Agent 的工具调用机制
2. **量化算法实现**：ARIMA、布林带、MACD 指标计算
3. **自适应可视化**：数据驱动的图表类型选择
4. **会话隔离设计**：多用户数据隔离方案
5. **工程化实践**：错误处理、安全格式化、模块化设计

### 核心代码位置

- 工具注册：`assistant_stock_bot.py` 第 182-259 行（exc_sql）
- ARIMA 预测：`assistant_stock_bot.py` 第 262-501 行
- 布林带检测：`assistant_stock_bot.py` 第 504-702 行
- 图表生成：`assistant_stock_bot.py` 第 705-793 行

### 扩展方向

- 实时数据对接（Tushare Pro）
- 深度学习预测模型（LSTM）
- 多因子策略回测
- 消息推送通知（飞书/钉钉）
- 用户权限管理