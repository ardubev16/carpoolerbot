from collections.abc import Sequence

import telegram
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from carpoolerbot.database import Session
from carpoolerbot.database.models import DbUser, Poll, PollAnswer
from carpoolerbot.poll_report.types import NotVotedError, ReturnTime


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


def upsert_poll_answers(poll_id: str, selected_options: Sequence[int], user: telegram.User) -> None:
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
        )
        for option_id in range(len(poll_options))
    ]

    with Session.begin() as s:
        s.merge(DbUser.from_telegram_user(user))
        for answer in answers:
            s.merge(answer)


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
        raise NotVotedError(user_id, poll_id, poll_option_id)

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
        raise NotVotedError(user_id, poll_id, poll_option_id)

    with Session.begin() as s:
        poll_answer.return_time = return_time
        s.add(poll_answer)


def set_driver_id(user_id: int, poll_id: str, poll_option_id: int, driver_id: int, *, toggle: bool = False) -> None:
    with Session() as s:
        poll_answer = s.scalars(
            select(PollAnswer).where(
                PollAnswer.user_id == user_id,
                PollAnswer.poll_id == poll_id,
                PollAnswer.poll_option_id == poll_option_id,
            ),
        ).first()

    if not poll_answer:
        raise NotVotedError(user_id, poll_id, poll_option_id)

    if toggle and poll_answer.driver_id == driver_id:
        poll_answer.driver_id = None
    else:
        poll_answer.driver_id = driver_id

    with Session.begin() as s:
        s.add(poll_answer)
