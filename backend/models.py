from sqlalchemy import String, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class Task(Base):
    __tablename__ = 'tasks'
    __table_args__ = (
        CheckConstraint("priority BETWEEN 1 AND 4", name="ck_tasks_priority_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(1000))
    priority: Mapped[int] = mapped_column(default=2, server_default='2')
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(50), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(200))