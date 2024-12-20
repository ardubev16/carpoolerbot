import logging
from datetime import datetime

import telegram
from telegram import Bot, Update, constants
from telegram.ext import ContextTypes

from carpoolerbot.actions import send_poll, send_whos_tomorrow
from carpoolerbot.database import DbHelper, DeleteResult, InsertResult, with_db
from carpoolerbot.message_serializers import full_poll_result, whos_tomorrow_text
from carpoolerbot.models import PollReportType
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

    await update.effective_message.delete()
    await send_poll(update.get_bot(), update.effective_chat.id)


@with_db
async def get_poll_results_cmd(db_helper: DbHelper, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat

    latest_poll_id = db_helper.get_latest_poll_id(update.effective_chat.id)
    if not latest_poll_id:
        await update.effective_chat.send_message("No Polls found.")
        return

    latest_poll = db_helper.get_poll_results(latest_poll_id)
    poll_report = await update.effective_chat.send_message(
        full_poll_result(latest_poll),
        parse_mode=constants.ParseMode.HTML,
    )
    db_helper.insert_poll_report(latest_poll_id, poll_report, PollReportType.FULL_WEEK)


async def update_poll_reports(db_helper: DbHelper, bot: Bot, poll_id: str) -> None:
    poll_reports = db_helper.get_poll_reports(poll_id)
    latest_poll = db_helper.get_poll_results(poll_id)

    for report in poll_reports:
        match report.message_type:
            case PollReportType.SINGLE_DAY:
                day_of_the_week = datetime.fromtimestamp(report.sent_timestamp).weekday()
                text = whos_tomorrow_text(latest_poll, day_of_the_week)
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


@with_db
async def handle_poll_answer(db_helper: DbHelper, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.poll_answer
    assert update.poll_answer.user

    poll_id = update.poll_answer.poll_id
    answering_user_id = update.poll_answer.user.id
    selected_options = update.poll_answer.option_ids

    if not selected_options:
        db_helper.delete_poll_answers(poll_id, answering_user_id)
        logger.info("User %s retracted his vote", answering_user_id)
    else:
        logger.info("Handling poll update")
        for option_id in selected_options:
            db_helper.insert_poll_answer(poll_id, option_id, update.poll_answer.user)
            logger.info("Inserted answer %s by user %s, poll_id = %s", option_id, answering_user_id, poll_id)

    await update_poll_reports(db_helper, update.get_bot(), poll_id)


@with_db
async def drive_cmd(db_helper: DbHelper, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_message
    assert update.effective_user

    match db_helper.insert_designated_driver(update.effective_message.chat_id, update.effective_user):
        case InsertResult.SUCCESS:
            await update.effective_message.reply_text("You are now a designated driver.", disable_notification=True)
        case InsertResult.ALREADY_EXIST:
            await update.effective_message.reply_text("You are already a designated driver.", disable_notification=True)


@with_db
async def nodrive_cmd(db_helper: DbHelper, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_message
    assert update.effective_user

    match db_helper.delete_designated_driver(update.effective_message.chat_id, update.effective_user.id):
        case DeleteResult.DELETED:
            await update.effective_message.reply_text(
                "You are no longer a designated driver.",
                disable_notification=True,
            )
        case DeleteResult.NOT_FOUND:
            await update.effective_message.reply_text("You were not a designated driver.", disable_notification=True)


async def whos_tomorrow_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat

    await send_whos_tomorrow(update.get_bot(), update.effective_chat.id)
