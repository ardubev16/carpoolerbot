#!/usr/bin/env python3

import argparse
import logging
from datetime import datetime

import telegram
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings
from telegram import Bot, Update, constants
from telegram.ext import Application, CallbackContext, CommandHandler, ContextTypes, PollAnswerHandler

from carpooler.actions import send_poll, send_whos_tomorrow
from carpooler.apscheduler_sqlalchemy_adapter import PTBSQLAlchemyJobStore
from carpooler.database import DbHelper, DeleteResult, InsertResult, init_db, with_db
from carpooler.message_serializers import full_poll_result, whos_tomorrow_text
from carpooler.models import PollReportType

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    TELEGRAM_TOKEN: str = Field(default=...)
    DB_PATH: str = Field(default=":memory:")


WEEKDAYS_POLL = "weekdays_poll"


@with_db
async def post_init(db_helper: DbHelper, app: Application) -> None:
    db_helper.create_tables()
    await app.bot.set_my_commands(
        (
            ("poll", "Manually send the weekly Poll."),
            ("get_poll_results", "Get results to last Poll."),
            ("whos_tomorrow", "Return the people on site tomorrow."),
            ("drive", "Show you as a Designated Driver."),
            ("nodrive", "Remove you from the Designated Driver list."),
            ("enable_schedule", "Send weekly poll on Sunday and tomorrow's people at set time."),
            ("disable_schedule", "Disable automatic messages."),
        ),
    )


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

    await send_whos_tomorrow(context.bot, context.job.chat_id)


async def send_poll_callback(context: CallbackContext) -> None:
    assert context.job
    assert context.job.chat_id

    await send_poll(context.bot, context.job.chat_id)


async def enable_schedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert context.job_queue
    assert update.effective_chat
    assert update.effective_message

    chat_id = update.effective_message.chat_id
    if jobs_exist(str(chat_id), context):
        await update.effective_chat.send_message(
            "Schedule is already present, delete it first.",
            disable_notification=True,
        )
        return

    parser = argparse.ArgumentParser(exit_on_error=False)
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
    await update.effective_chat.send_message(message_text, disable_notification=True)


async def disable_schedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat
    assert update.effective_message

    job_removed = remove_job_if_exists(str(update.effective_message.chat_id), context)
    message_text = "Schedule has been disabled." if job_removed else "Schedule was not enabled."
    await update.effective_chat.send_message(message_text, disable_notification=True)


def main() -> None:
    load_dotenv()
    settings = Settings()
    init_db(settings.DB_PATH)

    application = Application.builder().token(settings.TELEGRAM_TOKEN).post_init(post_init).build()

    if settings.DB_PATH != ":memory:":
        assert application.job_queue
        application.job_queue.scheduler.add_jobstore(
            PTBSQLAlchemyJobStore(application=application, url="sqlite:///" + settings.DB_PATH),
        )
    application.add_handler(CommandHandler("poll", poll_cmd))
    application.add_handler(CommandHandler("get_poll_results", get_poll_results_cmd))
    application.add_handler(CommandHandler("whos_tomorrow", whos_tomorrow_cmd))
    application.add_handler(CommandHandler("drive", drive_cmd))
    application.add_handler(CommandHandler("nodrive", nodrive_cmd))
    application.add_handler(CommandHandler("enable_schedule", enable_schedule_cmd))
    application.add_handler(CommandHandler("disable_schedule", disable_schedule_cmd))
    application.add_handler(PollAnswerHandler(handle_poll_answer))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
