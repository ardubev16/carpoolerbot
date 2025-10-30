import logging

import telegram
from telegram.ext import CallbackContext, ContextTypes

from carpoolerbot.poll.common import send_poll
from carpoolerbot.poll_report.common import send_daily_poll_report

logger = logging.getLogger(__name__)

type CallbackContextType = CallbackContext[telegram.Bot, None, None, None]


def jobs_exist(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    assert context.job_queue
    return bool(context.job_queue.get_jobs_by_name(name))


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    assert context.job_queue

    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def send_whos_tomorrow_callback(context: CallbackContextType) -> None:
    """
    Send daily poll report with error handling.

    This callback is resilient to database connectivity issues and other errors.
    Errors are logged but don't prevent future scheduled executions.
    """
    assert context.job
    assert context.job.chat_id

    try:
        await send_daily_poll_report(context.bot, context.job.chat_id)
        logger.info("Successfully sent daily poll report to chat %s", context.job.chat_id)
    except Exception:
        logger.exception(
            "Failed to send daily poll report to chat %s. Will retry on next scheduled run.",
            context.job.chat_id,
        )


async def send_poll_callback(context: CallbackContextType) -> None:
    """
    Send poll with error handling.

    This callback is resilient to database connectivity issues and other errors.
    Errors are logged but don't prevent future scheduled executions.
    """
    assert context.job
    assert context.job.chat_id

    try:
        await send_poll(context.bot, context.job.chat_id)
        logger.info("Successfully sent poll to chat %s", context.job.chat_id)
    except Exception:
        logger.exception(
            "Failed to send poll to chat %s. Will retry on next scheduled run.",
            context.job.chat_id,
        )
