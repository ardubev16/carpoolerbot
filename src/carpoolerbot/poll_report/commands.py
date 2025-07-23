from telegram import Update, constants
from telegram.ext import ContextTypes

from carpoolerbot.database.repositories.poll import get_latest_poll
from carpoolerbot.database.repositories.poll_answers import get_all_poll_answers
from carpoolerbot.database.repositories.poll_reports import insert_poll_report
from carpoolerbot.poll_report.handlers import send_daily_poll_report
from carpoolerbot.poll_report.message_serializers import full_poll_result


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
