from telegram import Bot

from carpoolerbot.database import Session
from carpoolerbot.database.models import Poll
from carpoolerbot.database.repositories.misc import get_latest_poll


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
