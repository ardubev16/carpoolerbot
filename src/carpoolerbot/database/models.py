from __future__ import annotations

from typing import TYPE_CHECKING, Self

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

if TYPE_CHECKING:
    from telegram import User


class Base(DeclarativeBase):
    pass


class DbUser(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_fullname: Mapped[str] = mapped_column()

    @classmethod
    def from_telegram_user(cls, user: User) -> Self:
        return cls(
            user_id=user.id,
            user_fullname=user.full_name,
        )


class Poll(Base):
    __tablename__ = "polls"

    poll_id: Mapped[str] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(BigInteger)
    options: Mapped[list[str]] = mapped_column(JSON)
    is_open: Mapped[bool] = mapped_column(default=True)

    poll_reports: Mapped[list[PollReport]] = relationship(back_populates="poll")
    poll_answers: Mapped[list[PollAnswer]] = relationship(back_populates="poll")


class PollReport(Base):
    __tablename__ = "poll_reports"

    poll_id: Mapped[str] = mapped_column(ForeignKey("polls.poll_id"))
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    message_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    poll_option_id: Mapped[int | None]
    sent_timestamp: Mapped[int]

    poll: Mapped[Poll] = relationship(back_populates="poll_reports")


class PollAnswer(Base):
    __tablename__ = "poll_answers"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), primary_key=True)
    poll_id: Mapped[str] = mapped_column(ForeignKey("polls.poll_id"), primary_key=True)
    poll_option_id: Mapped[int] = mapped_column(primary_key=True)
    poll_answer: Mapped[bool]

    override_answer: Mapped[bool | None] = mapped_column(default=None)
    driver_id: Mapped[int | None] = mapped_column(BigInteger, default=None)
    return_time: Mapped[int] = mapped_column(default=0)

    user: Mapped[DbUser] = relationship()
    poll: Mapped[Poll] = relationship(back_populates="poll_answers")
