import argparse
import logging

from apscheduler.triggers.cron import CronTrigger
from telegram import Update
from telegram.ext import CallbackContext, ContextTypes

from carpoolerbot.actions import send_poll
from carpoolerbot.poll_reports.handlers import send_daily_poll_report

logger = logging.getLogger(__name__)


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


async def send_whos_tomorrow_callback(context: CallbackContext) -> None:
    assert context.job
    assert context.job.chat_id

    await send_daily_poll_report(context.bot, context.job.chat_id)


async def send_poll_callback(context: CallbackContext) -> None:
    assert context.job
    assert context.job.chat_id

    await send_poll(context.bot, context.job.chat_id)


async def enable_schedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert context.job_queue
    assert update.effective_chat
    assert update.effective_message
    assert update.effective_user

    chat_id = update.effective_message.chat_id
    if jobs_exist(str(chat_id), context):
        await update.effective_chat.send_message(
            "Schedule is already present, delete it first.",
            disable_notification=True,
        )
        return

    parser = argparse.ArgumentParser(exit_on_error=False, add_help=False)
    parser.add_argument("poll_hour", type=int)
    parser.add_argument("tomorrow_message_hour", type=int)

    try:
        args = parser.parse_args(context.args)
    except argparse.ArgumentError:
        await update.effective_chat.send_message(
            "Usage: /enable_schedule <poll_hour> <tomorrow_message_hour>",
            disable_notification=True,
        )
        return

    context.job_queue.run_custom(
        send_poll_callback,
        {"trigger": CronTrigger(day_of_week="sun", hour=args.poll_hour)},
        chat_id=chat_id,
        name=str(chat_id),
    )
    context.job_queue.run_custom(
        send_whos_tomorrow_callback,
        {"trigger": CronTrigger(day_of_week="sun, mon-thu", hour=args.tomorrow_message_hour)},
        chat_id=chat_id,
        name=str(chat_id),
    )
    message_text = f"""\
Schedule has been enabled with the following settings:

- Poll will be sent every Sunday at {args.poll_hour}:00.
- Tomorrow's people message will be sent at {args.tomorrow_message_hour}:00."""
    logger.info("User %s enabled schedule in chat %s", update.effective_user.id, chat_id)
    await update.effective_chat.send_message(message_text, disable_notification=True)


async def disable_schedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat
    assert update.effective_message
    assert update.effective_user

    chat_id = update.effective_message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    message_text = "Schedule has been disabled." if job_removed else "Schedule was not enabled."
    logger.info("User %s disabled schedule in chat %s", update.effective_user.id, chat_id)
    await update.effective_chat.send_message(message_text, disable_notification=True)
