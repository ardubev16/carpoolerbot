import argparse
import logging

from apscheduler.triggers.cron import CronTrigger
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from carpoolerbot.scheduling.common import (
    jobs_exist,
    remove_job_if_exists,
    send_poll_callback,
    send_whos_tomorrow_callback,
)
from carpoolerbot.utils import TypedBaseHandler

logger = logging.getLogger(__name__)


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


def handlers() -> list[TypedBaseHandler]:
    return [
        CommandHandler("enable_schedule", enable_schedule_cmd),
        CommandHandler("disable_schedule", disable_schedule_cmd),
    ]


commands = (
    ("enable_schedule", "Send weekly poll on Sunday and tomorrow's people at set time."),
    ("disable_schedule", "Disable automatic messages."),
)
