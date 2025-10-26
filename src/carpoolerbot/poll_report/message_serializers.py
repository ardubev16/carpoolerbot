import calendar
import datetime
from collections import defaultdict
from collections.abc import Sequence

import holidays

from carpoolerbot.database.models import PollAnswer
from carpoolerbot.poll_report.types import ReturnTime


def format_user_answer(answer: PollAnswer) -> str:
    formatted_user = answer.user.user_fullname

    if answer.driver_id == answer.user_id:
        formatted_user = f"🚗 {formatted_user}"
    elif answer.driver_id == -1:
        formatted_user = f"👤 {formatted_user}"

    match ReturnTime(answer.return_time):
        case ReturnTime.AFTER_WORK:
            pass
        case ReturnTime.AFTER_DINNER:
            formatted_user = f"🍽 {formatted_user}"
        case ReturnTime.LATE:
            formatted_user = f"🎯 {formatted_user}"

    return f'<a href="tg://user?id={answer.user_id}">{formatted_user}</a>'


def sorted_positive_answers(answers: Sequence[PollAnswer]) -> list[PollAnswer]:
    return sorted(
        filter(lambda x: x.poll_answer and x.override_answer is not False, answers),
        key=lambda x: x.user.user_fullname.lower(),
    )


def whos_on_text(poll_answers: Sequence[PollAnswer], day: datetime.datetime) -> str:
    day_of_the_week = day.weekday()

    if day_of_the_week in (calendar.SATURDAY, calendar.SUNDAY):
        return "You are not working tomorrow, are you?"

    day_name = calendar.day_name[day_of_the_week]

    # TODO: hardcoded country and subdiv, would be nice if it was configurable
    # https://github.com/ardubev16/carpoolerbot/issues/7
    if holiday := holidays.country_holidays("IT", subdiv="BZ").get(day):
        return f"I hope you are on holiday tomorrow, happy <b>{holiday}</b>!"

    relevant_answers = sorted_positive_answers(poll_answers)
    if len(relevant_answers) == 0:
        return f"Nobody is going on site on <b>{day_name}</b>."

    formatted_users = [
        format_user_answer(answer) for answer in sorted(relevant_answers, key=lambda x: x.user.user_fullname.lower())
    ]

    return f"""\
On <b>{day_name}</b> is going on site:

{"\n".join(formatted_users)}"""


def full_poll_result(poll_answers: Sequence[PollAnswer]) -> str:
    grouped_answers: dict[int, list[PollAnswer]] = defaultdict(list)
    for answer in poll_answers:
        grouped_answers[answer.poll_option_id].append(answer)

    formatted_days_answers = [
        f"<b>{calendar.day_name[day]}</b>:\n"
        + "\n".join(format_user_answer(answer) for answer in sorted_positive_answers(answers))
        for day, answers in sorted(grouped_answers.items(), key=lambda x: x[0])
    ]

    return "\n\n".join(formatted_days_answers)
