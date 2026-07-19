import logging

import telegram.error
from telegram import Bot

from carpoolerbot.database import Session
from carpoolerbot.database.models import WeeklyPoll
from carpoolerbot.database.repositories.poll import close_poll, get_latest_poll

logger = logging.getLogger(__name__)


async def send_poll(bot: Bot, chat_id: int) -> None:
    if latest_poll := get_latest_poll(chat_id):
        try:
            await bot.stop_poll(chat_id, latest_poll.message_id)
            await bot.unpin_chat_message(chat_id, latest_poll.message_id)
        except telegram.error.BadRequest:
            logger.warning(
                "Failed to stop/unpin poll with message_id %s in chat_id %s",
                latest_poll.message_id,
                chat_id,
            )

        close_poll(chat_id, latest_poll.message_id)

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
            WeeklyPoll(
                chat_id=chat_id,
                message_id=message.id,
                poll_id=message.poll.id,
                options=options,
            ),
        )
