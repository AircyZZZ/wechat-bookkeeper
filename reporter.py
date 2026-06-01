"""统计报表生成 — 纯文本格式，含字符进度条。"""

from datetime import date, datetime

from db import get_today_expenses, get_today_total, get_month_stats, get_month_total
from category_kb import CATEGORY_EMOJI

BAR_WIDTH = 20  # 进度条总宽度（字符数）


def _bar(ratio: float, width: int = BAR_WIDTH) -> str:
    """生成字符进度条。

    Args:
        ratio: 0.0 ~ 1.0
        width: 总宽度

    Returns:
        如 "████████████░░░░░░░░"
    """
    filled = int(ratio * width)
    empty = width - filled
    return "█" * filled + "░" * empty


def _emoji(category: str) -> str:
    """获取分类对应 emoji。"""
    return CATEGORY_EMOJI.get(category, "📌")


def report_today(openid: str) -> str:
    """生成今日开销报表。

    Returns:
        多行文本，含明细和合计
    """
    today = date.today()
    expenses = get_today_expenses(openid)
    total = get_today_total(openid)

    if not expenses:
        return f"📅 {today.month}月{today.day}日\n\n还没有记账哦～\n发「午饭25元」试试吧"

    lines = [f"📅 今日开销 ({today.month}月{today.day}日)\n"]
    for exp in expenses:
        emoji = _emoji(exp.category)
        lines.append(f"  {emoji} {exp.description:　<6s} ¥{exp.amount:.2f}")
    lines.append(f"  {'─' * 18}")
    lines.append(f"  💰 合计 ¥{total:.2f}  |  {len(expenses)} 笔")

    return "\n".join(lines)


def report_month(openid: str) -> str:
    """生成本月统计报表。

    Returns:
        多行文本，含分类占比文字图表
    """
    now = datetime.now()
    stats = get_month_stats(openid)
    total = get_month_total(openid)

    if not stats:
        return f"📊 {now.month}月统计\n\n还没有任何开销记录～"

    # 计算当月天数（用于日均）
    days_in_month = {
        1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
        7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31,
    }
    days = days_in_month.get(now.month, 30)
    avg_per_day = total / max(now.day, 1)

    lines = [f"📊 {now.month}月统计\n"]

    for category, info in stats.items():
        cat_total = info["total"]
        count = info["count"]
        ratio = cat_total / total if total > 0 else 0
        emoji = _emoji(category)

        lines.append(
            f"  {emoji} {category:　<4s} ¥{cat_total:>8.2f}  "
            f"{_bar(ratio)}  {ratio:.0%}"
        )

    lines.append(f"  {'─' * 35}")
    lines.append(f"  💰 合计 ¥{total:.2f}  |  日均 ¥{avg_per_day:.0f}")

    return "\n".join(lines)


def report_help() -> str:
    """生成帮助信息。"""
    return """📖 记账 Bot 使用指南

💬 记账 — 直接说：
    午饭25元
    咖啡36
    地铁6块
    打车 ¥50

📅 查询 — 发送：
    今日  → 今日开销明细
    本月  → 本月分类统计

🗑 撤销 — 发送：
    撤销  → 删除最近一笔

📌 支持的分类：
    餐饮🍜 交通🚇 购物🛒
    娱乐🎬 居住🏠 医疗💊
    教育📚 其他📌"""


def report_recorded(amount: float, category: str, description: str, openid: str) -> str:
    """生成记账确认消息。"""
    emoji = _emoji(category)
    today_total = get_today_total(openid)
    return f"✅ 已记录：{emoji} {category} ¥{amount:.2f}\n   ── {description}\n💰 今日累计 ¥{today_total:.2f}"


def report_undo(record) -> str:
    """生成撤销确认消息。"""
    if record is None:
        return "🤷 没有可撤销的记录"
    emoji = _emoji(record.category)
    return f"🗑 已撤销：{emoji} {record.category} ¥{record.amount:.2f}\n   ── {record.description}"
