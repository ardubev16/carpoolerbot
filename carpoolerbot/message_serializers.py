import calendar

from carpoolerbot.database import SimpleUser


def whos_tomorrow_text(latest_poll: list[tuple[str, list[SimpleUser]]], day_of_the_week: int) -> str:
    tomorrow = (day_of_the_week + 1) % 7
    if tomorrow in (calendar.SATURDAY, calendar.SUNDAY):
        return "You are not working tomorrow, are you?"

    day_name, users = latest_poll[tomorrow]
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
