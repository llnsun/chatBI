# ChatBI-Assistant-nanobot-cli

基于 nanobot 框架的智能股票量化分析助手。支持自然语言交互，提供 SQL 查询、ARIMA 预测、布林带检测、实时行情等能力。

## 项目结构

```
ChatBI-Assistant-nanobot-cli/
├── agent.py                  # CLI 入口（核心逻辑：建库、注册工具、运行 Agent）
├── app_gui.py                # Gradio Web UI（端口 7861）
├── config.json               # nanobot 配置（模型、密钥、工具权限）
├── stock_history.db          # SQLite 股票历史数据库
│
├── tools/                    # 自定义工具（注册到 Agent）
│   ├── __init__.py
│   ├── exc_sql.py            # SQL 查询 + 自动可视化
│   ├── arima_stock.py        # ARIMA 时间序列预测
│   ├── boll_detection.py     # 布林带超买超卖检测
│   └── get_stock_realtime.py # Tushare 实时行情
│
├── skills/                   # 技能定义（指导 LLM 的工具调用策略）
│   ├── arima-predict/
│   │   └── SKILL.md          # ARIMA 预测技能
│   ├── boll-detect/
│   │   └── SKILL.md          # 布林带检测技能
│   └── sql-query/
│       └── SKILL.md          # SQL 查询技能
│
├── utils/                    # 工具函数
│   ├── __init__.py
│   ├── chart.py              # 图表生成（柱状图/折线图/ARIMA/布林带）
│   └── stock_resolver.py     # 股票名称→代码解析 + 自动拉取
│
├── sessions/                 # 会话记录（不提交 Git）
│   ├── gradio_default.jsonl
│   └── stock_run.jsonl
│
└── image_show/               # 图表输出目录（不提交 Git）
```

## 核心功能

### 1. SQL 查询 (`exc_sql`)

自然语言 → SQL → 表格 + 可视化图表。

```
用户: "贵州茅台2025年的收盘价走势如何？"
Agent: 生成 SQL → 查询 stock_history → 返回表格 + 折线图
```

- 数据量 ≤ 10 条：完整表格
- 数据量 > 10 条：前5行 + 后5行 + 描述统计
- 多股票：按股票分组显示
- 图表类型自适应：≤ 20 条 → 柱状图，> 20 条 → 折线图

### 2. ARIMA 预测 (`arima_stock`)

基于历史收盘价的时间序列预测。

- 模型：ARIMA(5,1,5)，失败降级到 (2,1,2)
- 输出：预测表格 + 历史+预测曲线 + 95% 置信区间
- 需要 ≥ 30 条历史数据
- 预测天数：1-365（默认 5 天）

### 3. 布林带检测 (`boll_detection`)

MA20 ± 2σ 超买超卖信号识别。

- 需要 ≥ 20 条数据
- 超买信号：收盘价 > 上轨
- 超卖信号：收盘价 < 下轨
- 输出：检测摘要 + 超买/超卖详情 + 可视化图表

### 4. 实时行情 (`get_stock_realtime`)

通过 Tushare API 获取最新交易日行情。

- 输入：股票代码或名称
- 输出：开盘价/收盘价/最高价/最低价/涨跌幅 + 柱状图

## 快速开始

### 环境要求

```bash
pip install nanobot pandas sqlalchemy matplotlib numpy statsmodels tushare gradio
```

### 配置

1. 获取 [DashScope API Key](https://dashscope.console.aliyun.com/)
2. 获取 [Tushare Token](https://tushare.pro/register)

```bash
# Windows
set DASHSCOPE_API_KEY=你的API_KEY
set TUSHARE_TOKEN=你的TUSHARE_TOKEN

# Linux/Mac
export DASHSCOPE_API_KEY=你的API_KEY
export TUSHARE_TOKEN=你的TUSHARE_TOKEN
```

### 运行

```bash
# CLI 模式 - 单次问答
python agent.py "贵州茅台2025年的收盘价走势如何？"

# Gradio Web UI - 浏览器访问 http://localhost:7861
python app_gui.py
```

### 示例查询

```
# 历史数据查询
"贵州茅台2025年的收盘价走势如何？"
"对比贵州茅台和五粮液2025年的收盘价"

# 价格预测
"预测贵州茅台未来10天的收盘价走势"

# 异常检测
"检测贵州茅台2025年的异常点"
"检测中芯国际过去一年的超买超卖信号"

# 实时行情
"贵州茅台最新价格是多少？"
"五粮液今日行情如何？"
```

## 数据库结构

### stock_history 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键自增 |
| 交易日期 | TEXT | YYYYMMDD |
| 股票名称 | TEXT | 中文名称 |
| 股票代码 | TEXT | 如 600519.SH |
| 开盘价 | REAL | 开盘价格 |
| 最高价 | REAL | 最高价格 |
| 最低价 | REAL | 最低价格 |
| 收盘价 | REAL | 收盘价格 |
| 昨收价 | REAL | 昨日收盘 |
| 涨跌额 | REAL | 涨跌金额 |
| 涨跌幅 | REAL | 涨跌幅度(%) |
| 成交量 | REAL | 成交量 |
| 成交额 | REAL | 成交金额 |

数据库首次启动时自动创建，并尝试从 Tushare 拉取预定义股票的近一年数据。

## 配置说明

[config.json](file:///e:/code/aiapp/12-ChatBI/chatBI/ChatBI-Assistant-nanobot-cli/config.json)

| 配置项 | 值 | 说明 |
|--------|-----|------|
| `model` | qwen3.7-plus | LLM 模型 |
| `max_tokens` | 4096 | 单次最大输出 token |
| `temperature` | 0 | 生成温度（0=确定性） |
| `max_tool_iterations` | 20 | 工具调用最大轮次 |
| `timezone` | Asia/Shanghai | 时区 |

## 技术架构

```
用户输入 (Gradio / CLI)
    │
    ▼
nanobot AgentLoop ── 技能匹配 ── 工具调用 ── 结果渲染
    │
    ├── exc_sql          → SQLite 查询 → 表格 + Matplotlib 图表
    ├── arima_stock      → statsmodels ARIMA → 预测曲线 + 置信区间
    ├── boll_detection   → 布林带计算 → 信号标记图
    └── get_stock_realtime → Tushare API → 实时行情表 + 柱状图
```

## 与 Qwen Agent 版的区别

| 维度 | nanobot 版 (本项目) | Qwen Agent 版 |
|------|:---:|:---:|
| 代码组织 | 模块化（tools/skills/utils） | 单文件（1000+ 行） |
| 技能系统 | SKILL.md 定义 | 无 |
| CLI 支持 | `python agent.py "问题"` | 仅 Gradio |
| 工具注册 | `loop.tools.register()` | `@register_tool` 装饰器 |
| 扩展性 | 高 | 低 |
