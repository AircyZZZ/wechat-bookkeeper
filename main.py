"""微信记账 Bot — FastAPI 入口。"""

from contextlib import asynccontextmanager
import uuid

from fastapi import FastAPI, Request, Response, Query

from config import PORT, HOST, WECHAT_TOKEN
from wechat import verify_signature, parse_message, build_reply
from parser import dispatch, ExpenseResult, CommandResult, UnknownResult
from db import setup_database, add_expense, delete_latest
from reporter import (
    report_today,
    report_month,
    report_help,
    report_recorded,
    report_undo,
)

import uvicorn


# ── 应用生命周期 ──

@asynccontextmanager
async def lifespan(application: FastAPI):
    """启动时初始化数据库。"""
    setup_database()
    yield


app = FastAPI(title="记账 Bot", version="0.1.0", lifespan=lifespan)


# ── 核心：消息处理 ──

def process_message(user_id: str, text: str) -> str:
    """处理一条消息文本，返回回复文本。"""
    result = dispatch(text)

    if isinstance(result, ExpenseResult):
        add_expense(user_id, result.amount, result.category, result.description)
        return report_recorded(result.amount, result.category, result.description, user_id)

    elif isinstance(result, CommandResult):
        if result.cmd == "today":
            return report_today(user_id)
        elif result.cmd == "month":
            return report_month(user_id)
        elif result.cmd == "help":
            return report_help()
        elif result.cmd == "undo":
            record = delete_latest(user_id)
            return report_undo(record)
        else:
            return report_help()

    elif isinstance(result, UnknownResult):
        return f"🤔 没太看懂「{text}」\n\n{report_help()}"

    return report_help()


# ── 健康检查 ──

@app.get("/")
async def root():
    return {"status": "ok", "app": "记账 Bot"}


# ── 微信测试号接入（已有，不动） ──

@app.get("/wechat")
async def wechat_verify(
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
):
    """微信服务器接入验证（GET）。"""
    if verify_signature(WECHAT_TOKEN, signature, timestamp, nonce):
        return Response(content=echostr)
    return Response(content="signature verification failed", status_code=403)


@app.post("/wechat")
async def wechat_message(request: Request):
    """接收并处理微信用户消息（POST）。"""
    xml_body = await request.body()
    msg = parse_message(xml_body.decode())

    if not msg:
        return Response(content="success")

    reply = process_message(msg.from_user, msg.content)
    reply_xml = build_reply(msg.from_user, msg.to_user, reply)
    return Response(content=reply_xml, media_type="application/xml")


# ── OpenAI 兼容端点（给 OpenClaw 用） ──

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI 兼容的 Chat Completions API。

    OpenClaw 通过此端点把微信 ClawBot 的消息转给记账 Bot 处理。
    """
    body = await request.json()

    # 提取最后一条用户消息
    messages = body.get("messages", [])
    user_text = ""
    user_id = "clawbot_user"  # ClawBot 不传 openid，统一用户
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_text = msg.get("content", "")
            break

    # 如果有对话中的 metadata 可以取用户 ID
    user = body.get("user", "")
    if user:
        user_id = user

    # 处理消息
    reply = process_message(user_id, user_text)

    # 返回 OpenAI 格式响应
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": 0,
        "model": body.get("model", "expense-bot"),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": reply},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }


# ── 启动入口 ──

if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
