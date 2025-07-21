from collections.abc import Sequence

import telegram
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from carpoolerbot.database import Session
from carpoolerbot.database.models import DbUser, Poll, PollAnswer


def get_all_poll_answers(poll_id: str) -> Sequence[PollAnswer]:
    with Session() as s:
        poll_answers = s.scalars(
            select(PollAnswer)
            .options(selectinload(PollAnswer.user))
            .options(selectinload(PollAnswer.poll))
            .where(PollAnswer.poll_id == poll_id),
        ).all()

    if not poll_answers:
        return []

    return poll_answers


def delete_poll_answers(poll_id: str, user_id: int) -> None:
    with Session.begin() as s:
        s.execute(delete(PollAnswer).where(PollAnswer.poll_id == poll_id, PollAnswer.user_id == user_id))


def insert_poll_answers(poll_id: str, selected_options: Sequence[int], user: telegram.User) -> None:
    with Session() as s:
        poll_options = s.scalars(select(Poll.options).where(Poll.poll_id == poll_id)).first()

    if poll_options is None:
        msg = f"Poll with ID {poll_id} does not exist or has no options."
        raise ValueError(msg)

    answers = [
        PollAnswer(
            user_id=user.id,
            poll_id=poll_id,
            poll_option_id=option_id,
            poll_answer=option_id in selected_options,
            return_time=0,
        )
        for option_id in range(len(poll_options))
    ]

    with Session.begin() as s:
        s.merge(DbUser.from_telegram_user(user))
        s.add_all(answers)
