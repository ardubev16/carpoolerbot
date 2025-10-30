from sqlalchemy import select

from carpoolerbot.database import Session
from carpoolerbot.database.models import WeeklyPoll
from carpoolerbot.database.retry import retry_on_db_error


def get_latest_poll(chat_id: int) -> WeeklyPoll | None:
    def _get_latest_poll() -> WeeklyPoll | None:
        with Session() as s:
            return s.scalars(
                select(WeeklyPoll).where(WeeklyPoll.chat_id == chat_id).order_by(WeeklyPoll.message_id.desc()),
            ).first()

    return retry_on_db_error(_get_latest_poll)


def close_poll(chat_id: int, message_id: int) -> None:
    def _close_poll() -> None:
        with Session() as s:
            poll = s.scalars(
                select(WeeklyPoll).where(WeeklyPoll.chat_id == chat_id, WeeklyPoll.message_id == message_id),
            ).first()

        if poll:
            with Session.begin() as s:
                poll.is_open = False
                s.add(poll)

    retry_on_db_error(_close_poll)
