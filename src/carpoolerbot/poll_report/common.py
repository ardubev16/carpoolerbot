import asyncio
import datetime
import logging
from collections.abc import Sequence

import telegram
from telegram import InlineKeyboardMarkup, constants

from carpoolerbot.database.models import PollAnswer, PollReport
from carpoolerbot.database.repositories.poll import get_latest_poll
from carpoolerbot.database.repositories.poll_answers import get_all_poll_answers
from carpoolerbot.database.repositories.poll_reports import get_all_poll_reports, insert_poll_report
from carpoolerbot.poll_report.message_serializers import full_poll_result, whos_on_text
from carpoolerbot.poll_report.types import DAILY_MSG_KEYBOARD_DEFAULT

logger = logging.getLogger(__name__)


async def update_all_poll_reports(bot: telegram.Bot, poll_id: str) -> None:
    poll_reports = get_all_poll_reports(poll_id)
    latest_poll = get_all_poll_answers(poll_id)

    for report in poll_reports:
        await update_poll_report(bot, latest_poll, report)


async def update_poll_report(bot: telegram.Bot, poll_answers: Sequence[PollAnswer], poll_report: PollReport) -> None:
    match poll_report.poll_option_id:
        case None:
            text = full_poll_result(poll_answers)
            reply_markup = None

        case _:
            day_after_sent_report = datetime.datetime.fromtimestamp(poll_report.sent_timestamp) + datetime.timedelta(
                days=1,
            )
            text = whos_on_text(poll_answers, day_after_sent_report)
            reply_markup = InlineKeyboardMarkup(DAILY_MSG_KEYBOARD_DEFAULT)

    try:
        await bot.edit_message_text(
            chat_id=poll_report.chat_id,
            message_id=poll_report.message_id,
            text=text,
            parse_mode=constants.ParseMode.HTML,
            reply_markup=reply_markup,
        )
        await asyncio.sleep(0.2)
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
