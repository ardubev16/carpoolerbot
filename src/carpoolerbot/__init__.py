#!/usr/bin/env python3

import logging

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from telegram import Update
from telegram.ext import Application, CommandHandler, PollAnswerHandler

from carpoolerbot import commands, schedules
from carpoolerbot.apscheduler_sqlalchemy_adapter import PTBSQLAlchemyJobStore
from carpoolerbot.database import DbHelper, init_db, with_db

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    TELEGRAM_TOKEN: str = Field(default=...)
    DB_PATH: str = Field(default=":memory:")


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


def main() -> None:
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    settings = Settings()
    init_db(settings.DB_PATH)

    application = Application.builder().token(settings.TELEGRAM_TOKEN).post_init(post_init).build()

    if settings.DB_PATH != ":memory:":
        assert application.job_queue
        application.job_queue.scheduler.add_jobstore(
            PTBSQLAlchemyJobStore(application=application, url="sqlite:///" + settings.DB_PATH),
        )
    application.add_handler(CommandHandler("poll", commands.poll_cmd))
    application.add_handler(CommandHandler("get_poll_results", commands.get_poll_results_cmd))
    application.add_handler(CommandHandler("whos_tomorrow", commands.whos_tomorrow_cmd))
    application.add_handler(CommandHandler("drive", commands.drive_cmd))
    application.add_handler(CommandHandler("nodrive", commands.nodrive_cmd))
    application.add_handler(CommandHandler("enable_schedule", schedules.enable_schedule_cmd))
    application.add_handler(CommandHandler("disable_schedule", schedules.disable_schedule_cmd))
    application.add_handler(PollAnswerHandler(commands.handle_poll_answer))

    application.run_polling(allowed_updates=Update.ALL_TYPES)
