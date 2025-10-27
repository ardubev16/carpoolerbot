import logging

from telegram import Update, constants
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from carpoolerbot.database.repositories.poll import get_latest_poll
from carpoolerbot.database.repositories.poll_answers import (
    get_all_poll_answers,
    set_driver_id,
    set_override_answer,
    set_return_time,
)
from carpoolerbot.database.repositories.poll_reports import get_poll_report, insert_poll_report
from carpoolerbot.poll_report.common import send_daily_poll_report, update_poll_report
from carpoolerbot.poll_report.message_serializers import full_poll_result
from carpoolerbot.poll_report.types import (
    DAILY_MSG_HELP,
    DailyReportCommands,
    NotVotedError,
    PollNotFoundError,
    ReturnTime,
)
from carpoolerbot.utils import TypedBaseHandler

logger = logging.getLogger(__name__)


async def get_poll_results_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat

    latest_poll = get_latest_poll(update.effective_chat.id)
    if not latest_poll:
        await update.effective_chat.send_message("No Polls found.")
        return

    latest_poll_results = get_all_poll_answers(latest_poll.poll_id)

    poll_report = await update.effective_chat.send_message(
        full_poll_result(latest_poll_results),
        parse_mode=constants.ParseMode.HTML,
    )
    insert_poll_report(latest_poll.poll_id, poll_report, poll_option_id=None)


async def whos_tomorrow_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat

    await send_daily_poll_report(update.get_bot(), update.effective_chat.id)


async def daily_poll_report_callback_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:  # noqa: C901
    assert update.callback_query
    assert update.effective_chat
    assert update.effective_message
    assert update.effective_user

    user_id = update.effective_user.id

    try:
        poll_report = get_poll_report(update.effective_chat.id, update.effective_message.id)
    except PollNotFoundError as e:
        logger.error("Poll not found, could be older than the bot's first start: %s", e)
        await update.callback_query.answer("Poll not found.")
        return

    poll_id = poll_report.poll_id
    poll_option_id = poll_report.poll_option_id

    assert poll_option_id is not None  # This should always be set for daily reports

    if not poll_report.weekly_poll.is_open:
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
            case DailyReportCommands.ALONE:
                set_driver_id(user_id, poll_id, poll_option_id, -1, toggle=True)
            case DailyReportCommands.WORK:
                set_return_time(user_id, poll_id, poll_option_id, ReturnTime.AFTER_WORK)
            case DailyReportCommands.DINNER:
                set_return_time(user_id, poll_id, poll_option_id, ReturnTime.AFTER_DINNER)
            case DailyReportCommands.LATE:
                set_return_time(user_id, poll_id, poll_option_id, ReturnTime.LATE)
            case DailyReportCommands.HELP:
                await update.callback_query.answer(DAILY_MSG_HELP, show_alert=True)
                return

    except NotVotedError as e:
        logger.info("User %s tried to interact with daily report without voting: %s", user_id, e)
        await update.callback_query.answer(f"You have not voted in the latest poll (id={e.poll_id}).", show_alert=True)
        return

    await update.callback_query.answer()

    await update_poll_report(update.get_bot(), get_all_poll_answers(poll_id), poll_report)


def handlers() -> list[TypedBaseHandler]:
    return [
        CommandHandler("get_poll_results", get_poll_results_cmd),
        CommandHandler("whos_tomorrow", whos_tomorrow_cmd),
        CallbackQueryHandler(daily_poll_report_callback_handler, lambda x: x in DailyReportCommands),
    ]


commands = (
    ("get_poll_results", "Get results to last Poll."),
    ("whos_tomorrow", "Return the people on site tomorrow."),
)
