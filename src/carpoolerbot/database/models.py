from __future__ import annotations

from typing import TYPE_CHECKING, Self

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

if TYPE_CHECKING:
    from telegram import User


class Base(DeclarativeBase):
    pass


class DbUser(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    user_fullname: Mapped[str] = mapped_column()

    @classmethod
    def from_telegram_user(cls, user: User) -> Self:
        return cls(
            user_id=user.id,
            user_fullname=user.full_name,
        )


class Poll(Base):
    __tablename__ = "polls"

    chat_id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int]
    poll_id: Mapped[str] = mapped_column(primary_key=True)
    options: Mapped[list[str]] = mapped_column(JSON)

    poll_reports: Mapped[list[PollReport]] = relationship(back_populates="poll")
    poll_answers: Mapped[list[PollAnswer]] = relationship(back_populates="poll")


class PollReport(Base):
    __tablename__ = "poll_reports"

    poll_id: Mapped[str] = mapped_column(ForeignKey("polls.poll_id"))
    chat_id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(primary_key=True)
    sent_timestamp: Mapped[int]
    message_type: Mapped[int]

    poll: Mapped[Poll] = relationship(back_populates="poll_reports")


class PollAnswer(Base):
    __tablename__ = "poll_answers"

    poll_id: Mapped[str] = mapped_column(ForeignKey("polls.poll_id"), primary_key=True)
    option_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)

    user: Mapped[DbUser] = relationship()
    poll: Mapped[Poll] = relationship(back_populates="poll_answers")


class DesignatedDriver(Base):
    __tablename__ = "designated_drivers"

    chat_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)

    user: Mapped[DbUser] = relationship()
