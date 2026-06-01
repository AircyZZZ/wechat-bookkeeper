"""应用配置 — 从环境变量读取。"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── 微信测试号配置 ──
# 在 mp.weixin.qq.com/debug/cgi-bin/sandbox?t=sandbox/login 获取
WECHAT_TOKEN = os.getenv("WECHAT_TOKEN", "your_token_here")

# ── 数据库 ──
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bookkeeper.db")

# ── Claude API (可选 fallback) ──
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── 服务器 ──
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
