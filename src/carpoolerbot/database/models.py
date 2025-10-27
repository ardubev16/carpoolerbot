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


class WeeklyPoll(Base):
    __tablename__ = "weekly_polls"

    poll_id: Mapped[str] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(BigInteger)
    options: Mapped[list[str]] = mapped_column(JSON)
    is_open: Mapped[bool] = mapped_column(default=True)

    poll_reports: Mapped[list[PollReport]] = relationship(back_populates="weekly_poll")
    poll_answers: Mapped[list[PollAnswer]] = relationship(back_populates="weekly_poll")


class PollReport(Base):
    __tablename__ = "poll_reports"

    poll_id: Mapped[str] = mapped_column(ForeignKey("weekly_polls.poll_id"))
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    message_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    poll_option_id: Mapped[int | None]
    sent_timestamp: Mapped[int]

    weekly_poll: Mapped[WeeklyPoll] = relationship(back_populates="poll_reports")


class PollAnswer(Base):
    __tablename__ = "poll_answers"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), primary_key=True)
    poll_id: Mapped[str] = mapped_column(ForeignKey("weekly_polls.poll_id"), primary_key=True)
    poll_option_id: Mapped[int] = mapped_column(primary_key=True)
    poll_answer: Mapped[bool]

    override_answer: Mapped[bool | None] = mapped_column(default=None)
    # This can get 4 kinds of values:
    #   - The user_id: this user is driving
    #   - Another user_id: this user is in another's car
    #   - -1: this user goes alone
    #   - None: default
    driver_id: Mapped[int | None] = mapped_column(BigInteger, default=None)
    return_time: Mapped[int] = mapped_column(default=0)

    user: Mapped[DbUser] = relationship()
    weekly_poll: Mapped[WeeklyPoll] = relationship(back_populates="poll_answers")
