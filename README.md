# ChatBI - 智能量化分析助手

基于大语言模型的股票智能分析系统，提供两个独立实现版本。

## 项目概览

```
chatBI/
├── ChatBI-Assistant/                  # Qwen Agent 版（Gradio + Qwen Agent 框架）
│   ├── assistant_stock_bot.py         # 股票助手主程序
│   ├── assistant_ticket_bot-3.py      # 门票订单助手
│   ├── get_stock_data.py              # Tushare 数据获取
│   ├── import_excel_to_db.py          # Excel 数据导入
│   └── ...
│
└── ChatBI-Assistant-nanobot-cli/      # nanobot 版（Gradio + nanobot 框架）
    ├── agent.py                       # CLI 入口
    ├── app_gui.py                     # Gradio Web 界面
    ├── tools/                         # 自定义工具
    │   ├── exc_sql.py                 # SQL 查询 + 可视化
    │   ├── arima_stock.py             # ARIMA 价格预测
    │   ├── boll_detection.py          # 布林带异常检测
    │   └── get_stock_realtime.py      # 实时行情
    ├── skills/                        # 技能定义
    │   ├── arima-predict/
    │   ├── boll-detect/
    │   └── sql-query/
    └── utils/                         # 工具函数（图表生成、股票解析）
```

## 两个版本对比

| 特性 | ChatBI-Assistant | ChatBI-Assistant-nanobot-cli |
|------|:---:|:---:|
| **Agent 框架** | Qwen Agent | nanobot |
| **LLM 提供商** | DashScope | DashScope |
| **Web UI** | Gradio (端口 7863) | Gradio (端口 7861) |
| **CLI 模式** | 无 | `python agent.py "问题"` |
| **技能系统** | 无 | arima-predict / boll-detect / sql-query |
| **代码量** | 较大（单文件 1000+ 行） | 模块化（按功能拆分） |
| **扩展性** | 低 | 高（工具+技能可独立扩展） |

## 核心功能

- **SQL 查询**：自然语言转 SQL，自动生成柱状图/折线图
- **ARIMA 预测**：时间序列预测未来收盘价，含 95% 置信区间
- **布林带检测**：MA20 ± 2σ 超买超卖信号识别
- **实时行情**：Tushare 实时数据查询
- **多股票对比**：自动分组显示和对比图表

## 支持的股票

- 贵州茅台 (600519.SH)
- 五粮液 (000858.SZ)
- 广发证券 (000776.SZ)
- 中芯国际 (688981.SH)

## 快速开始

### 环境变量

```bash
set DASHSCOPE_API_KEY=你的API_KEY
set TUSHARE_TOKEN=你的TUSHARE_TOKEN
```

### 启动 nanobot 版（推荐）

```bash
cd ChatBI-Assistant-nanobot-cli

# Web 界面
python app_gui.py

# CLI 模式
python agent.py "贵州茅台2025年的收盘价走势如何？"
```

### 启动 Qwen Agent 版

```bash
cd ChatBI-Assistant
python assistant_stock_bot.py
```

## 技术栈

- **LLM**：通义千问 (DashScope)
- **数据源**：Tushare Pro API + SQLite
- **可视化**：Matplotlib
- **前端**：Gradio
- **量化算法**：ARIMA、布林带
