from collections.abc import Sequence

from sqlalchemy import select
from telegram import Message

from carpoolerbot.database.models import PollReport
from carpoolerbot.database.session import Session
from carpoolerbot.database.types import PollReportType


def insert_poll_report(poll_id: str, report_message: Message, report_type: PollReportType) -> None:
    with Session.begin() as s:
        s.add(
            PollReport(
                poll_id=poll_id,
                chat_id=report_message.chat_id,
                message_id=report_message.id,
                sent_timestamp=report_message.date.timestamp(),
                message_type=report_type,
            ),
        )


def get_poll_reports(poll_id: str) -> Sequence[PollReport]:
    with Session() as s:
        return s.scalars(select(PollReport).where(PollReport.poll_id == poll_id)).all()
