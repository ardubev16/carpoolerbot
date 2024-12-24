import calendar
import datetime

import holidays

from carpoolerbot.database import SimpleUser


def whos_on_text(latest_poll: list[tuple[str, list[SimpleUser]]], day: datetime.datetime) -> str:
    day_of_the_week = day.weekday()
    if day_of_the_week in (calendar.SATURDAY, calendar.SUNDAY):
        return "You are not working tomorrow, are you?"

    if holiday := holidays.country_holidays("IT", subdiv="BZ").get(day):
        return f"I hope you are on holiday tomorrow, happy <b>{holiday}</b>!"

    day_name, users = latest_poll[day_of_the_week]
    if len(users) == 0:
        return f"Nobody is going on site on <b>{day_name}</b>."

    return f"""\
On <b>{day_name}</b> is going on site:

{"\n".join(user.mention_html() for user in users)}"""


def full_poll_result(latest_poll: list[tuple[str, list[SimpleUser]]]) -> str:
    days: list[str] = []
    for option, users in latest_poll:
        days.append(f"""\
<b>{option}:</b>
  {"\n  ".join(user.mention_html() for user in users)}""")

    return "\n\n".join(days)
