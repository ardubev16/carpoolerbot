from datetime import datetime

from telegram import Bot, constants

from carpooler.database import DbHelper, with_db
from carpooler.message_serializers import whos_tomorrow_text
from carpooler.models import PollInstance, PollReportType


@with_db
async def send_whos_tomorrow(db_helper: DbHelper, bot: Bot, chat_id: int) -> None:
    latest_poll_id = db_helper.get_latest_poll_id(chat_id)
    if not latest_poll_id:
        await bot.send_message(chat_id, "No Polls found.")
        return

    latest_poll = db_helper.get_poll_results(latest_poll_id)
    day_of_the_week = datetime.today().weekday()

    poll_report = await bot.send_message(
        chat_id,
        whos_tomorrow_text(latest_poll, day_of_the_week),
        parse_mode=constants.ParseMode.HTML,
    )
    db_helper.insert_poll_report(latest_poll_id, poll_report, PollReportType.SINGLE_DAY)


@with_db
async def send_poll(db_helper: DbHelper, bot: Bot, chat_id: int) -> None:
    if latest_poll_msg_id := db_helper.get_latest_poll_message_id(chat_id):
        await bot.stop_poll(chat_id, latest_poll_msg_id)
        await bot.unpin_chat_message(chat_id, latest_poll_msg_id)

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

    db_helper.insert_new_poll(
        PollInstance(
            chat_id=chat_id,
            message_id=message.id,
            poll_id=message.poll.id,
            options=options,
        ),
    )
