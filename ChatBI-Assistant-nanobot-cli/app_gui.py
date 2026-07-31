#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票查询助手 - Gradio Web UI（流式版）

运行: python app_gui.py
访问: http://localhost:7868
"""

import asyncio
import os
import queue
import re
import sys
import threading
from pathlib import Path

if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import gradio as gr
from agent import WORKSPACE, init_database, build_loop

IMAGE_SHOW_DIR = WORKSPACE / "image_show"
IMAGE_SHOW_DIR.mkdir(exist_ok=True)


import base64

def _fix_image_paths(text: str) -> str:
    """修复图片路径：转为 base64 嵌入，确保 Gradio 可渲染"""
    def _replace(m):
        alt = m.group(1) or "图表"
        img_path = m.group(2)
        if img_path.startswith('file='):
            img_path = img_path[5:]
        p = Path(img_path)
        if not p.is_absolute():
            p = (WORKSPACE / p).resolve()
        if p.exists():
            with open(p, 'rb') as f:
                b64_data = base64.b64encode(f.read()).decode('utf-8')
            return f'![{alt}](data:image/png;base64,{b64_data})'
        else:
            return f"_[图片未找到: {p.name}]_\n"
    return re.sub(r'!\[(.*?)\]\(([^)]+)\)', _replace, text)


def chat_handler(message: str, history: list):
    """流式对话处理器（Generator），支持：
    1. 用户消息立即显示
    2. 工具调用进度展示
    3. LLM 输出逐字流式显示
    """
    if not message or not message.strip():
        return history

    # 创建基础 history（包含用户消息），后续所有状态都基于此构建
    base_history = list(history) + [{"role": "user", "content": message}]
    yield base_history

    # 跨线程通信队列
    q: queue.Queue = queue.Queue()

    def _run_agent():
        """在独立线程中运行异步 agent"""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)

        async def _task():
            agent_loop = build_loop()

            async def on_progress(text: str, **kwargs):
                q.put(("progress", text))

            async def on_stream(delta: str):
                q.put(("stream", delta))

            async def on_stream_end(*, resuming: bool = False):
                pass

            result = await agent_loop.process_direct(
                message,
                session_key="gradio:default",
                on_progress=on_progress,
                on_stream=on_stream,
                on_stream_end=on_stream_end,
            )
            q.put(("done", result))

        new_loop.run_until_complete(_task())
        new_loop.close()

    t = threading.Thread(target=_run_agent, daemon=True)
    t.start()

    accumulated = ""
    latest_progress: str = ""

    while t.is_alive() or not q.empty():
        try:
            msg_type, data = q.get(timeout=0.15)
        except queue.Empty:
            # 等待中：显示最新进度提示
            display = latest_progress if latest_progress else " 思考中..."
            yield base_history + [{"role": "assistant", "content": display}]
            continue

        if msg_type == "progress":
            latest_progress = f"✦ {data}"
            yield base_history + [{"role": "assistant", "content": latest_progress}]

        elif msg_type == "stream":
            accumulated += data
            yield base_history + [{"role": "assistant", "content": accumulated}]

        elif msg_type == "done":
            result = data
            final_text = result.content if result and result.content else "抱歉，未能生成回复。"
            final_text = _fix_image_paths(final_text)
            yield base_history + [{"role": "assistant", "content": final_text}]
            break

    t.join(timeout=1)


def clear_history():
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

        # 事件绑定 - 使用 generator 实现流式
        submit_btn.click(
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
    print(f"  本地访问: http://localhost:7868")
    print(f"  图片目录: {IMAGE_SHOW_DIR}")
    print("=" * 50)

    os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
    os.environ["no_proxy"] = "localhost,127.0.0.1,0.0.0.0"

    demo.queue(default_concurrency_limit=3).launch(
        server_name="0.0.0.0",
        server_port=7868,
        share=False,
        show_error=True,
        quiet=True,
        show_api=False,
        allowed_paths=[str(IMAGE_SHOW_DIR)],
    )


if __name__ == "__main__":
    main()
