#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票查询助手 - Gradio Web UI

运行: python app_gui.py
访问: http://localhost:7861
"""

import asyncio
import os
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import gradio as gr
from agent import (DB_PATH, DEFAULT_STOCKS, WORKSPACE,
                   PrintHook, init_database, build_bot)

_session_raw_history: list[dict] = []

IMAGE_SHOW_DIR = WORKSPACE / "image_show"
IMAGE_SHOW_DIR.mkdir(exist_ok=True)


def _make_image_paths_absolute(text: str) -> str:
    """将 Markdown 图片引用中的相对路径转为 Gradio file= 格式"""
    def _replace(m):
        alt = m.group(1) or "图片"
        img_path = m.group(2)
        if not os.path.isabs(img_path):
            img_path = str(WORKSPACE / img_path)
        img_path = os.path.normpath(img_path)
        if os.path.exists(img_path):
            return f"![{alt}](file={img_path})"
        else:
            return f"_[图片未找到]_\n"
    return re.sub(r'!\[(.*?)\]\(([^)]+)\)', _replace, text)


async def _do_chat(message: str) -> str:
    """异步执行一次对话，返回响应文本"""
    session_id = "gradio:default"
    _session_raw_history.append({"role": "user", "content": message})

    bot = build_bot()

    if len(_session_raw_history) > 1:
        context_parts = []
        for h in _session_raw_history[:-1]:
            role_label = "用户" if h["role"] == "user" else "助手"
            context_parts.append(f"{role_label}: {h['content'][:500]}")
        prompt = f"对话历史:\n{chr(10).join(context_parts)}\n\n用户最新问题: {message}"
    else:
        prompt = message

    try:
        result = await bot.run(prompt, session_key=session_id, hooks=[PrintHook()])
        response_text = result.content or "抱歉，未能生成回复。"
    except Exception as e:
        response_text = f"处理请求时出错: {str(e)}"

    _session_raw_history.append({"role": "assistant", "content": response_text})
    return _make_image_paths_absolute(response_text)


def chat_handler(message: str, history: list):
    """同步包装，Gradio 事件回调"""
    if not message or not message.strip():
        return history

    # 用 asyncio 运行异步任务
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    response_text = loop.run_until_complete(_do_chat(message))

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": response_text})
    return history


def clear_history():
    """清空对话历史"""
    _session_raw_history.clear()
    return []


def create_ui():
    """创建 Gradio 界面"""
    custom_css = """
    .main-header { text-align: center; margin-bottom: 1rem; }
    .main-header h1 { font-size: 1.8rem; color: #1f77b4; margin-bottom: 0.3rem; }
    .main-header p { color: #666; font-size: 0.9rem; }
    footer { display: none !important; }
    """

    with gr.Blocks(
        css=custom_css,
        title="股票查询助手",
        theme=gr.themes.Soft(primary_hue="blue"),
    ) as demo:
        gr.HTML("""
        <div class="main-header">
            <h1>股票查询助手</h1>
            <p>支持自然语言查询 · ARIMA 预测 · 布林带检测 · 实时行情</p>
        </div>
        """)

        chatbot = gr.Chatbot(
            height=600,
            type="messages",
            render_markdown=True,
            show_copy_button=True,
        )

        with gr.Row():
            msg = gr.Textbox(
                placeholder="请输入你的股票问题，例如：贵州茅台2025年的收盘价走势如何？",
                scale=8,
                show_label=False,
                container=False,
            )
            submit_btn = gr.Button("发送", variant="primary", scale=1, min_width=80)

        with gr.Row():
            clear_btn = gr.Button("清空对话", variant="secondary", size="sm")

        gr.Examples(
            examples=[
                "贵州茅台2025年的收盘价走势如何？",
                "对比贵州茅台和五粮液2025年的收盘价",
                "预测贵州茅台未来10天的收盘价走势",
                "检测贵州茅台2025年的异常点",
                "检测中芯国际过去一年的超买超卖信号",
                "贵州茅台最新价格是多少？",
            ],
            inputs=msg,
            label="试试这些问题",
        )

        gr.Markdown("""
        ---
        **支持的股票**: 贵州茅台(600519.SH) · 五粮液(000858.SZ) · 广发证券(000776.SZ) · 中芯国际(688981.SH)
        &nbsp;&nbsp;|&nbsp;&nbsp;
        也可查询其他股票，系统会自动从 Tushare 拉取数据
        """)

        # 事件绑定
        send_fn = submit_btn.click(
            fn=chat_handler,
            inputs=[msg, chatbot],
            outputs=[chatbot],
        )

        msg.submit(
            fn=chat_handler,
            inputs=[msg, chatbot],
            outputs=[chatbot],
        )

        # 发送后清空输入框
        submit_btn.click(fn=lambda: "", outputs=[msg], queue=False)
        msg.submit(fn=lambda: "", outputs=[msg], queue=False)

        clear_btn.click(
            fn=clear_history,
            outputs=[chatbot],
        )

    return demo


def main():
    """启动 Gradio 服务"""
    print("正在初始化...")
    init_database()

    demo = create_ui()

    print("=" * 50)
    print("  股票查询助手 Web UI 已启动")
    print(f"  本地访问: http://localhost:7861")
    print(f"  图片目录: {IMAGE_SHOW_DIR}")
    print("=" * 50)

    demo.queue(default_concurrency_limit=3).launch(
        server_name="0.0.0.0",
        server_port=7861,
        share=False,
        show_error=True,
        allowed_paths=[str(IMAGE_SHOW_DIR)],
    )


if __name__ == "__main__":
    main()
