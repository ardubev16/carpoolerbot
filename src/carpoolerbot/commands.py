import logging

import telegram
from telegram import Update
from telegram.ext import ContextTypes

from carpoolerbot.actions import send_poll
from carpoolerbot.database.repositories.poll_answers import upsert_poll_answers
from carpoolerbot.poll_report.handlers import update_poll_reports
from carpoolerbot.schedules import jobs_exist

logger = logging.getLogger(__name__)


async def poll_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat
    assert update.effective_message

    if jobs_exist(str(update.effective_chat.id), context):
        await update.effective_chat.send_message(
            "Schedule is enabled, to manually send poll, disable schedule first.",
            disable_notification=True,
        )
        return

    try:
        await update.effective_message.delete()
    except telegram.error.BadRequest:
        await update.effective_chat.send_message(
            "I don't have permission to delete messages in this chat.",
            disable_notification=True,
        )
        return

    await send_poll(update.get_bot(), update.effective_chat.id)


async def handle_poll_answer(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.poll_answer
    assert update.poll_answer.user

    poll_id = update.poll_answer.poll_id
    answering_user = update.poll_answer.user

    logger.info("Handling poll update")
    upsert_poll_answers(poll_id, update.poll_answer.option_ids, answering_user)
    logger.info("Updated answers of user %s, poll_id = %s", answering_user.id, poll_id)

    await update_poll_reports(update.get_bot(), poll_id)
