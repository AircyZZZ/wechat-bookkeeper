"""数据模型定义。"""

from datetime import datetime
from sqlalchemy import create_engine, Integer, Float, Text, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

from config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


class Expense(Base):
    """支出记录。"""

    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_openid: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False, default="其他")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )

    def __repr__(self):
        return f"<Expense {self.category} ¥{self.amount} {self.description}>"


class Category(Base):
    """分类关键词配置。"""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    keywords: Mapped[str] = mapped_column(Text, nullable=False, default="")

    def __repr__(self):
        return f"<Category {self.name}>"


def init_db():
    """创建所有表。"""
    Base.metadata.create_all(engine)


def get_session() -> Session:
    """获取数据库会话。"""
    return Session(engine)
