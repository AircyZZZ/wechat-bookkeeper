"""微信记账 Bot — FastAPI 入口。"""

from contextlib import asynccontextmanager

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


# ── 健康检查 ──

@app.get("/")
async def root():
    return {"status": "ok", "app": "记账 Bot"}


# ── 微信接入 ──

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

    # ── 路由：消息 → 解析 → 执行 → 回复 ──
    result = dispatch(msg.content)

    if isinstance(result, ExpenseResult):
        add_expense(msg.from_user, result.amount, result.category, result.description)
        reply = report_recorded(result.amount, result.category, result.description, msg.from_user)

    elif isinstance(result, CommandResult):
        if result.cmd == "today":
            reply = report_today(msg.from_user)
        elif result.cmd == "month":
            reply = report_month(msg.from_user)
        elif result.cmd == "help":
            reply = report_help()
        elif result.cmd == "undo":
            record = delete_latest(msg.from_user)
            reply = report_undo(record)
        else:
            reply = report_help()

    elif isinstance(result, UnknownResult):
        # 无法识别 → 返回帮助
        reply = f"🤔 没太看懂「{msg.content}」\n\n{report_help()}"

    else:
        reply = report_help()

    # ── 构造微信 XML 回复 ──
    reply_xml = build_reply(msg.from_user, msg.to_user, reply)
    return Response(content=reply_xml, media_type="application/xml")


# ── 启动入口 ──

if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
