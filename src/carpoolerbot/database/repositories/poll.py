from sqlalchemy import select

from carpoolerbot.database import Session
from carpoolerbot.database.models import Poll


def get_latest_poll(chat_id: int) -> Poll | None:
    with Session() as s:
        return s.scalars(
            select(Poll).where(Poll.chat_id == chat_id).order_by(Poll.message_id.desc()),
        ).first()


def close_poll(chat_id: int, message_id: int) -> None:
    with Session() as s:
        poll = s.scalars(
            select(Poll).where(Poll.chat_id == chat_id, Poll.message_id == message_id),
        ).first()

    if poll:
        with Session.begin() as s:
            poll.is_open = False
            s.add(poll)
