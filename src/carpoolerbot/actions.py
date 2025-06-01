import datetime

from telegram import Bot, constants

from carpoolerbot.database import Session
from carpoolerbot.database.models import Poll
from carpoolerbot.database.repositories.misc import get_latest_poll
from carpoolerbot.database.repositories.poll_answers import get_poll_results
from carpoolerbot.database.repositories.poll_reports import insert_poll_report
from carpoolerbot.database.types import PollReportType
from carpoolerbot.message_serializers import whos_on_text


async def send_whos_tomorrow(bot: Bot, chat_id: int) -> None:
    latest_poll = get_latest_poll(chat_id)

    if not latest_poll:
        await bot.send_message(chat_id, "No Polls found.")
        return

    latest_poll_results = get_poll_results(latest_poll.poll_id)
    assert latest_poll_results  # We already checked that latest_poll exists, so results must be there

    tomorrow = datetime.datetime.today() + datetime.timedelta(days=1)

    poll_report = await bot.send_message(
        chat_id,
        whos_on_text(latest_poll_results, tomorrow),
        parse_mode=constants.ParseMode.HTML,
    )

    insert_poll_report(latest_poll.poll_id, poll_report, PollReportType.SINGLE_DAY)


async def send_poll(bot: Bot, chat_id: int) -> None:
    if latest_poll := get_latest_poll(chat_id):
        await bot.stop_poll(chat_id, latest_poll.message_id)
        await bot.unpin_chat_message(chat_id, latest_poll.message_id)

    options = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    message = await bot.send_poll(
        chat_id,
        "When are you going on site this week?",
        options,
        is_anonymous=False,
        allows_multiple_answers=True,
    )
    await message.pin()
    assert message.poll

    with Session.begin() as s:
        s.add(
            Poll(
                chat_id=chat_id,
                message_id=message.id,
                poll_id=message.poll.id,
                options=options,
            ),
        )
