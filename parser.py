"""消息解析引擎：命令分发 + 账单 NLP 解析。"""

import re
import json
from dataclasses import dataclass
from typing import Literal, Union

from category_kb import match_category
from config import ANTHROPIC_API_KEY

# ── 金额提取正则 ──
# 支持：25元、¥25、25块、25.5、250 等
AMOUNT_PATTERNS = [
    re.compile(r"(\d+\.?\d*)\s*[元块钱]"),          # 25元 / 25块 / 25钱
    re.compile(r"[¥￥](\d+\.?\d*)"),                  # ¥25
    re.compile(r"(\d+\.?\d*)$"),                      # 纯数字结尾
]

# ── 命令关键词 ──
COMMAND_TODAY = {"今日", "今天", "今日开销", "今天开销", "jintian", "today"}
COMMAND_MONTH = {"本月", "月统计", "月开销", "月份", "benyue", "month"}
COMMAND_HELP = {"帮助", "help", "?", "？", "怎么用", "使用说明"}
COMMAND_UNDO = {"删除", "撤销", "撤回", "undo", "delete", "删掉"}


@dataclass
class ExpenseResult:
    """账单解析结果。"""
    amount: float
    category: str
    description: str


@dataclass
class CommandResult:
    """命令解析结果。"""
    type: Literal["command"]
    cmd: Literal["today", "month", "help", "undo"]
    raw: str  # 原始消息文本


@dataclass
class UnknownResult:
    """无法识别。"""
    type: Literal["unknown"]
    raw: str


ParseResult = Union[ExpenseResult, CommandResult, UnknownResult]


def dispatch(text: str) -> ParseResult:
    """顶层消息分发。

    顺序：
    1. 命中命令 → CommandResult
    2. 包含数字 → 尝试解析账单 → ExpenseResult
    3. 其他 → UnknownResult
    """
    text = text.strip()

    if not text:
        return UnknownResult(type="unknown", raw=text)

    # 命令匹配
    cmd = _match_command(text)
    if cmd:
        return CommandResult(type="command", cmd=cmd, raw=text)

    # 尝试账单解析
    expense = parse_expense(text)
    if expense:
        return expense

    return UnknownResult(type="unknown", raw=text)


def parse_expense(text: str) -> Union[ExpenseResult, None]:
    """从文本中提取金额和分类。

    Args:
        text: 如 "午饭25元"

    Returns:
        ExpenseResult 或 None（无法提取金额）
    """
    amount = _extract_amount(text)
    if amount is None:
        return None

    # 去掉金额部分，剩余作为描述
    description = _extract_description(text)

    # 规则匹配分类
    category = match_category(text)

    # 规则匹配不到 → LLM fallback
    if category == "其他" and description:
        category = _llm_fallback(description)

    return ExpenseResult(amount=amount, category=category, description=description)


def _extract_amount(text: str) -> Union[float, None]:
    """从文本中提取金额。"""
    for pattern in AMOUNT_PATTERNS:
        match = pattern.search(text)
        if match:
            return float(match.group(1))
    return None


def _extract_description(text: str) -> str:
    """提取描述：去掉金额和货币符号。"""
    # 去掉 ¥25 / 25元 / 25块 等
    cleaned = re.sub(r"[¥￥]\d+\.?\d*", "", text)
    cleaned = re.sub(r"\d+\.?\d*\s*[元块钱]", "", cleaned)
    cleaned = re.sub(r"\d+\.?\d*$", "", cleaned)
    cleaned = cleaned.strip()
    return cleaned or text  # 如果清空了就返回原文


def _match_command(text: str) -> Union[str, None]:
    """匹配命令，返回命令名。"""
    t = text.lower().strip()
    if t in COMMAND_TODAY:
        return "today"
    if t in COMMAND_MONTH:
        return "month"
    if t in COMMAND_HELP:
        return "help"
    if t in COMMAND_UNDO or t.startswith("删除") or t.startswith("撤销"):
        return "undo"
    # 模糊匹配
    if "今日" in t or "今天" in t:
        return "today"
    if "月" in t:
        return "month"
    if "删" in t or "撤" in t:
        return "undo"
    return None


def _llm_fallback(description: str) -> str:
    """LLM fallback：调用 Claude API 识别分类。

    仅在规则匹配失败时调用，日常高频说法走规则即可。
    如果没有配置 API key 则直接返回"其他"。
    """
    if not ANTHROPIC_API_KEY:
        return "其他"

    try:
        import httpx

        categories = ["餐饮", "交通", "购物", "娱乐", "居住", "医疗", "教育", "其他"]
        prompt = (
            f"你是一个记账分类助手。用户说了一个消费项目：「{description}」\n"
            f"请从以下分类中选择最合适的一个：{', '.join(categories)}\n"
            f"只回复分类名称，不要解释。"
        )

        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=5.0,
        )

        if response.status_code == 200:
            data = response.json()
            content = data["content"][0]["text"].strip()
            for cat in categories:
                if cat in content:
                    return cat
        return "其他"
    except Exception:
        return "其他"
