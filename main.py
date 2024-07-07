#!/usr/bin/env python3

import logging
from datetime import datetime

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, ContextTypes, PollAnswerHandler

from carpooler.database import DbHelper, DeleteResult, InsertResult, init_db, with_db
from carpooler.models import PollInstance

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
            ("poll", "Manually send the weekly Poll"),
            ("get_poll_results", "Get results to last Poll"),
            ("whos_tomorrow", "Return the people on site tomorrow."),
            ("drive", "Show you as a Designated Driver"),
            ("nodrive", "Remove you from the Designated Driver list"),
        ),
    )


@with_db
async def poll_cmd(db_helper: DbHelper, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.delete()
    if latest_poll_msg_id := db_helper.get_latest_poll_message_id(update.effective_chat.id):
        await context.bot.stop_poll(update.effective_chat.id, latest_poll_msg_id)
        await update.effective_chat.unpin_message(latest_poll_msg_id)

    options = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    message = await update.effective_chat.send_poll(
        "When are you going on site this week?",
        options,
        is_anonymous=False,
        allows_multiple_answers=True,
    )
    await message.pin()

    db_helper.insert_new_poll(
        PollInstance(
            chat_id=update.effective_chat.id,
            message_id=message.id,
            poll_id=message.poll.id,
            options=options,
        ),
    )


@with_db
async def get_poll_results_cmd(db_helper: DbHelper, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    latest_poll = db_helper.get_latest_poll_results(update.effective_chat.id)
    if not latest_poll:
        await update.effective_chat.send_message("No Polls found.")
        return

    days: list[str] = []
    for option, usernames in latest_poll:
        days.append(
            f"<b>{option}:</b> {" ".join(f"@{username}" for username in usernames)}",
        )
    await update.effective_chat.send_message("\n\n".join(days), parse_mode=constants.ParseMode.HTML)


@with_db
async def handle_poll_answer(db_helper: DbHelper, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    poll_id = update.poll_answer.poll_id
    answering_username = update.poll_answer.user.username
    selected_options = update.poll_answer.option_ids

    if not answering_username:
        msg = "Do not handle the tuple (user_id, full_name) yet!"
        raise NotImplementedError(msg)

    if not selected_options:
        db_helper.delete_poll_answers(poll_id, answering_username)
        logger.info("User %s retracted his vote", answering_username)
        return

    logger.info("Handling poll update")
    for option_id in selected_options:
        db_helper.insert_poll_answer(poll_id, option_id, answering_username)
        logger.info("Inserted answer %s by user %s, poll_id = %s", option_id, answering_username, poll_id)


@with_db
async def drive_cmd(db_helper: DbHelper, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    match db_helper.insert_designated_driver(update.effective_chat.id, update.effective_user.username):
        case InsertResult.SUCCESS:
            await update.effective_message.reply_text("You are now a designated driver.", disable_notification=True)
        case InsertResult.ALREADY_EXIST:
            await update.effective_message.reply_text("You are already a designated driver.", disable_notification=True)


@with_db
async def nodrive_cmd(db_helper: DbHelper, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    latest_poll = db_helper.get_latest_poll_results(update.effective_chat.id)
    if not latest_poll:
        await update.effective_chat.send_message("No Polls found.")
        return

    day_of_the_week = datetime.today().weekday()
    day_name, usernames = latest_poll[day_of_the_week]
    await update.effective_chat.send_message(
        f"""\
On <b>{day_name}</b> is going on site:

{"\n".join(usernames)}""",
        parse_mode=constants.ParseMode.HTML,
    )


@with_db
async def whos_tomorrow_cmd(db_helper: DbHelper, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    match db_helper.delete_designated_driver(update.effective_chat.id, update.effective_user.username):
        case DeleteResult.DELETED:
            await update.effective_message.reply_text(
                "You are no longer a designated driver.",
                disable_notification=True,
            )
        case DeleteResult.NOT_FOUND:
            await update.effective_message.reply_text("You were not a designated driver.", disable_notification=True)


def main() -> None:
    load_dotenv()
    settings = Settings()
    init_db(settings.DB_PATH)

    application = Application.builder().token(settings.TELEGRAM_TOKEN).post_init(post_init).build()
    application.add_handler(CommandHandler("poll", poll_cmd))
    application.add_handler(CommandHandler("get_poll_results", get_poll_results_cmd))
    application.add_handler(CommandHandler("whos_tomorrow", whos_tomorrow_cmd))
    application.add_handler(CommandHandler("drive", drive_cmd))
    application.add_handler(CommandHandler("nodrive", nodrive_cmd))
    application.add_handler(PollAnswerHandler(handle_poll_answer))

    # application.job_queue.run_custom()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
