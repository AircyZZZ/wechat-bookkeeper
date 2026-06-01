"""数据库操作层。"""

from datetime import datetime, date
from typing import Union
from sqlalchemy import func, desc

from models import Expense, Category, get_session, init_db


# ── 初始化 ──

def setup_database():
    """首次启动：建表 + 写入默认分类。"""
    init_db()
    session = get_session()
    try:
        # 只有空表时才写入初始分类
        if session.query(Category).count() == 0:
            _seed_categories(session)
    finally:
        session.close()


def _seed_categories(session):
    """写入内置分类关键词。"""
    from category_kb import CATEGORY_KEYWORDS
    for name, keywords in CATEGORY_KEYWORDS.items():
        session.add(Category(name=name, keywords=",".join(keywords)))
    session.commit()


# ── 写入 ──

def add_expense(openid: str, amount: float, category: str, description: str) -> Expense:
    """记录一条支出。"""
    session = get_session()
    try:
        exp = Expense(
            user_openid=openid,
            amount=amount,
            category=category,
            description=description,
        )
        session.add(exp)
        session.commit()
        session.refresh(exp)
        return exp
    finally:
        session.close()


# ── 删除 ──

def delete_latest(openid: str) -> Union[Expense, None]:
    """删除该用户最近一笔支出，返回被删除的记录。"""
    session = get_session()
    try:
        latest = (
            session.query(Expense)
            .filter(Expense.user_openid == openid)
            .order_by(desc(Expense.id))
            .first()
        )
        if latest:
            session.delete(latest)
            session.commit()
            # 分离出会话以便在外部使用属性
            exp_data = Expense(
                user_openid=latest.user_openid,
                amount=latest.amount,
                category=latest.category,
                description=latest.description,
            )
            exp_data.id = latest.id
            exp_data.created_at = latest.created_at
            return exp_data
        return None
    finally:
        session.close()


# ── 查询 ──

def get_today_expenses(openid: str) -> list[Expense]:
    """查询用户今日所有支出。"""
    today = date.today()
    session = get_session()
    try:
        return (
            session.query(Expense)
            .filter(
                Expense.user_openid == openid,
                func.date(Expense.created_at) == today,
            )
            .order_by(desc(Expense.id))
            .all()
        )
    finally:
        session.close()


def get_today_total(openid: str) -> float:
    """查询用户今日支出合计。"""
    today = date.today()
    session = get_session()
    try:
        result = (
            session.query(func.sum(Expense.amount))
            .filter(
                Expense.user_openid == openid,
                func.date(Expense.created_at) == today,
            )
            .scalar()
        )
        return result or 0.0
    finally:
        session.close()


def get_month_stats(openid: str, year: int = 0, month: int = 0) -> dict:
    """查询用户某月按分类汇总。

    Returns:
        {category: total_amount, ...}
    """
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    session = get_session()
    try:
        results = (
            session.query(
                Expense.category,
                func.sum(Expense.amount).label("total"),
                func.count(Expense.id).label("count"),
            )
            .filter(
                Expense.user_openid == openid,
                func.strftime("%Y", Expense.created_at) == str(year),
                func.strftime("%m", Expense.created_at) == f"{month:02d}",
            )
            .group_by(Expense.category)
            .order_by(desc("total"))
            .all()
        )
        return {
            cat: {"total": float(total), "count": int(count)}
            for cat, total, count in results
        }
    finally:
        session.close()


def get_month_total(openid: str, year: int = 0, month: int = 0) -> float:
    """查询用户某月支出总合计。"""
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    session = get_session()
    try:
        result = (
            session.query(func.sum(Expense.amount))
            .filter(
                Expense.user_openid == openid,
                func.strftime("%Y", Expense.created_at) == str(year),
                func.strftime("%m", Expense.created_at) == f"{month:02d}",
            )
            .scalar()
        )
        return result or 0.0
    finally:
        session.close()


def get_categories() -> list[Category]:
    """获取所有分类关键词配置。"""
    session = get_session()
    try:
        return session.query(Category).all()
    finally:
        session.close()
