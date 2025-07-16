import datetime
import logging

import telegram
from telegram import Bot, Update, constants
from telegram.ext import ContextTypes

from carpoolerbot.actions import send_poll, send_whos_tomorrow
from carpoolerbot.database.repositories.misc import get_latest_poll
from carpoolerbot.database.repositories.poll_answers import delete_poll_answers, get_poll_results, insert_poll_answers
from carpoolerbot.database.repositories.poll_reports import get_poll_reports, insert_poll_report
from carpoolerbot.database.types import PollReportType
from carpoolerbot.message_serializers import full_poll_result, whos_on_text
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


async def get_poll_results_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat

    latest_poll = get_latest_poll(update.effective_chat.id)
    if not latest_poll:
        await update.effective_chat.send_message("No Polls found.")
        return

    latest_poll_results = get_poll_results(latest_poll.poll_id)
    assert latest_poll_results is not None  # Should always be not None if poll exists

    poll_report = await update.effective_chat.send_message(
        full_poll_result(latest_poll_results),
        parse_mode=constants.ParseMode.HTML,
    )
    insert_poll_report(latest_poll.poll_id, poll_report, PollReportType.FULL_WEEK)


async def update_poll_reports(bot: Bot, poll_id: str) -> None:
    poll_reports = get_poll_reports(poll_id)
    latest_poll = get_poll_results(poll_id)
    if not latest_poll:
        logger.warning("No latest poll found for poll_id %s", poll_id)
        return

    for report in poll_reports:
        match PollReportType(report.message_type):
            case PollReportType.SINGLE_DAY:
                day_after_sent_report = datetime.datetime.fromtimestamp(report.sent_timestamp) + datetime.timedelta(
                    days=1,
                )
                text = whos_on_text(latest_poll, day_after_sent_report)
            case PollReportType.FULL_WEEK:
                text = full_poll_result(latest_poll)

        try:
            await bot.edit_message_text(
                chat_id=report.chat_id,
                message_id=report.message_id,
                text=text,
                parse_mode=constants.ParseMode.HTML,
            )
        except telegram.error.BadRequest as err:
            logger.info("%s %s", err, {"chat_id": report.chat_id, "message_id": report.message_id})


async def handle_poll_answer(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.poll_answer
    assert update.poll_answer.user

    poll_id = update.poll_answer.poll_id
    answering_user_id = update.poll_answer.user.id
    selected_options = update.poll_answer.option_ids

    if not selected_options:
        delete_poll_answers(poll_id, answering_user_id)
        logger.info("User %s retracted his vote", answering_user_id)
    else:
        logger.info("Handling poll update")
        insert_poll_answers(poll_id, selected_options, update.poll_answer.user)
        logger.info("Inserted %s answers by user %s, poll_id = %s", len(selected_options), answering_user_id, poll_id)

    await update_poll_reports(update.get_bot(), poll_id)


async def whos_tomorrow_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat

    await send_whos_tomorrow(update.get_bot(), update.effective_chat.id)
