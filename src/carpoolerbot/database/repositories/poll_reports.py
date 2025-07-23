from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from telegram import Message

from carpoolerbot.database.models import PollReport
from carpoolerbot.database.session import Session
from carpoolerbot.poll_report.types import PollNotFoundError


def insert_poll_report(poll_id: str, message: Message, *, poll_option_id: int | None) -> None:
    with Session.begin() as s:
        s.add(
            PollReport(
                poll_id=poll_id,
                poll_option_id=poll_option_id,
                chat_id=message.chat_id,
                message_id=message.id,
                sent_timestamp=message.date.timestamp(),
            ),
        )


def get_all_poll_reports(poll_id: str) -> Sequence[PollReport]:
    with Session() as s:
        return s.scalars(select(PollReport).where(PollReport.poll_id == poll_id)).all()


def get_poll_report(chat_id: int, message_id: int) -> PollReport:
    with Session() as s:
        report = s.scalar(
            select(PollReport)
            .options(selectinload(PollReport.poll))
            .where(
                PollReport.chat_id == chat_id,
                PollReport.message_id == message_id,
            ),
        )

    if report is None:
        raise PollNotFoundError(chat_id, message_id)

    return report
