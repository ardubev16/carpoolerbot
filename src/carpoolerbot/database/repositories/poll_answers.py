from collections.abc import Sequence

import telegram
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from carpoolerbot.database import Session
from carpoolerbot.database.models import DbUser, Poll, PollAnswer
from carpoolerbot.poll_reports.types import ReturnTime


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


def set_override_answer(user_id: int, poll_id: str, poll_option_id: int, *, value: bool) -> None:
    with Session() as s:
        poll_answer = s.scalars(
            select(PollAnswer).where(
                PollAnswer.user_id == user_id,
                PollAnswer.poll_id == poll_id,
                PollAnswer.poll_option_id == poll_option_id,
            ),
        ).first()

    if not poll_answer:
        msg = f"No poll answer found for user {user_id}, poll {poll_id}, option {poll_option_id}"
        raise ValueError(msg)

    with Session.begin() as s:
        poll_answer.override_answer = value
        s.add(poll_answer)


def set_return_time(user_id: int, poll_id: str, poll_option_id: int, return_time: ReturnTime) -> None:
    with Session() as s:
        poll_answer = s.scalars(
            select(PollAnswer).where(
                PollAnswer.user_id == user_id,
                PollAnswer.poll_id == poll_id,
                PollAnswer.poll_option_id == poll_option_id,
            ),
        ).first()

    if not poll_answer:
        msg = f"No poll answer found for user {user_id}, poll {poll_id}, option {poll_option_id}"
        raise ValueError(msg)

    with Session.begin() as s:
        poll_answer.return_time = return_time
        s.add(poll_answer)


def set_driver_id(user_id: int, poll_id: str, poll_option_id: int, driver_id: int) -> None:
    with Session() as s:
        poll_answer = s.scalars(
            select(PollAnswer).where(
                PollAnswer.user_id == user_id,
                PollAnswer.poll_id == poll_id,
                PollAnswer.poll_option_id == poll_option_id,
            ),
        ).first()

    if not poll_answer:
        msg = f"No poll answer found for user {user_id}, poll {poll_id}, option {poll_option_id}"
        raise ValueError(msg)

    with Session.begin() as s:
        poll_answer.driver_id = driver_id
        s.add(poll_answer)
