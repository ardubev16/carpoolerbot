import datetime
import logging

import telegram
from telegram import constants

from carpoolerbot.database.repositories.misc import get_latest_poll
from carpoolerbot.database.repositories.poll_answers import get_all_poll_answers
from carpoolerbot.database.repositories.poll_reports import get_poll_reports, insert_poll_report
from carpoolerbot.database.types import PollReportType
from carpoolerbot.message_serializers import full_poll_result, whos_on_text

logger = logging.getLogger(__name__)


async def update_poll_reports(bot: telegram.Bot, poll_id: str) -> None:
    poll_reports = get_poll_reports(poll_id)
    latest_poll = get_all_poll_answers(poll_id)

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


async def send_whos_tomorrow(bot: telegram.Bot, chat_id: int) -> None:
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
    )

    insert_poll_report(latest_poll.poll_id, poll_report, PollReportType.SINGLE_DAY)
