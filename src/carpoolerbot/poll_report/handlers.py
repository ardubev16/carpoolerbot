import datetime
import logging

import telegram
from telegram import InlineKeyboardMarkup, Update, constants
from telegram.ext import ContextTypes

from carpoolerbot.database.repositories.poll import get_latest_poll
from carpoolerbot.database.repositories.poll_answers import (
    get_all_poll_answers,
    set_driver_id,
    set_override_answer,
    set_return_time,
)
from carpoolerbot.database.repositories.poll_reports import get_all_poll_reports, get_poll_report, insert_poll_report
from carpoolerbot.poll_report.message_serializers import full_poll_result, whos_on_text
from carpoolerbot.poll_report.types import DAILY_MSG_KEYBOARD_DEFAULT, DailyReportCommands, NotVotedError, ReturnTime

logger = logging.getLogger(__name__)


async def update_poll_reports(bot: telegram.Bot, poll_id: str) -> None:
    poll_reports = get_all_poll_reports(poll_id)
    latest_poll = get_all_poll_answers(poll_id)

    for report in poll_reports:
        match report.poll_option_id:
            case None:
                text = full_poll_result(latest_poll)
                reply_markup = None

            case _:
                day_after_sent_report = datetime.datetime.fromtimestamp(report.sent_timestamp) + datetime.timedelta(
                    days=1,
                )
                text = whos_on_text(latest_poll, day_after_sent_report)
                reply_markup = InlineKeyboardMarkup(DAILY_MSG_KEYBOARD_DEFAULT)

        try:
            await bot.edit_message_text(
                chat_id=report.chat_id,
                message_id=report.message_id,
                text=text,
                parse_mode=constants.ParseMode.HTML,
                reply_markup=reply_markup,
            )
        except telegram.error.BadRequest as err:
            if (
                err.message != "Message is not modified: specified new message content and reply "
                "markup are exactly the same as a current content and reply markup of the message"
            ):
                raise


async def send_daily_poll_report(bot: telegram.Bot, chat_id: int) -> None:
    latest_poll = get_latest_poll(chat_id)

    if not latest_poll:
        await bot.send_message(chat_id, "No Polls found.")
        return

    latest_poll_results = get_all_poll_answers(latest_poll.poll_id)

    tomorrow = datetime.datetime.today() + datetime.timedelta(days=1)

    poll_report = await bot.send_message(
        chat_id,
        whos_on_text(latest_poll_results, tomorrow),
        parse_mode=constants.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(DAILY_MSG_KEYBOARD_DEFAULT),
    )

    insert_poll_report(latest_poll.poll_id, poll_report, poll_option_id=tomorrow.weekday())


async def daily_poll_report_callback_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.callback_query
    assert update.effective_chat
    assert update.effective_message
    assert update.effective_user

    user_id = update.effective_user.id

    poll_report = get_poll_report(update.effective_chat.id, update.effective_message.id)
    poll_id = poll_report.poll_id
    poll_option_id = poll_report.poll_option_id

    assert poll_option_id  # This should always be set for daily reports

    if not poll_report.poll.is_open:
        logger.info("User %s tried to interact with daily report belonging to closed poll: %s", user_id, poll_id)
        await update.callback_query.answer("This poll is closed.", show_alert=True)
        return

    try:
        match DailyReportCommands(update.callback_query.data):
            case DailyReportCommands.CONFIRM:
                set_override_answer(user_id, poll_id, poll_option_id, value=True)
            case DailyReportCommands.REJECT:
                set_override_answer(user_id, poll_id, poll_option_id, value=False)
            case DailyReportCommands.DRIVE:
                set_driver_id(user_id, poll_id, poll_option_id, user_id, toggle=True)
            case DailyReportCommands.WORK:
                set_return_time(user_id, poll_id, poll_option_id, ReturnTime.AFTER_WORK)
            case DailyReportCommands.DINNER:
                set_return_time(user_id, poll_id, poll_option_id, ReturnTime.AFTER_DINNER)
            case DailyReportCommands.LATE:
                set_return_time(user_id, poll_id, poll_option_id, ReturnTime.LATE)
    except NotVotedError as e:
        logger.info("User %s tried to interact with daily report without voting: %s", user_id, e)
        await update.callback_query.answer(f"You have not voted in the latest poll (id={e.poll_id}).", show_alert=True)
        return

    await update.callback_query.answer()

    await update_poll_reports(update.get_bot(), poll_id)
