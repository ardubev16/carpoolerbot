from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from telegram import User

from carpoolerbot.database import Session
from carpoolerbot.database.models import DbUser, Poll, PollAnswer
from carpoolerbot.database.types import SimpleUser


def get_poll_results(poll_id: str) -> list[tuple[str, list[SimpleUser]]] | None:
    with Session() as s:
        poll = s.scalars(
            select(Poll)
            .options(selectinload(Poll.poll_answers).selectinload(PollAnswer.user))
            .where(Poll.poll_id == poll_id)
            .order_by(Poll.message_id.desc()),
        ).first()

    if not poll:
        return None

    users_by_option: list[list[SimpleUser]] = [[] for _ in poll.options]
    for answer in poll.poll_answers:
        user = answer.user
        is_driver = False
        users_by_option[answer.option_id].append(SimpleUser(user.user_id, user.user_fullname, is_driver))

    return list(zip(poll.options, users_by_option, strict=True))


def delete_poll_answers(poll_id: str, user_id: int) -> None:
    with Session.begin() as s:
        s.execute(delete(PollAnswer).where(PollAnswer.poll_id == poll_id, PollAnswer.user_id == user_id))


def insert_poll_answers(poll_id: str, option_ids: Sequence[int], user: User) -> None:
    answers = [
        PollAnswer(
            poll_id=poll_id,
            option_id=option_id,
            user_id=user.id,
        )
        for option_id in option_ids
    ]

    with Session.begin() as s:
        s.merge(DbUser.from_telegram_user(user))
        s.add_all(answers)
