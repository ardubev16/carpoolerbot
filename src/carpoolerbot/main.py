import importlib.metadata
import logging

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, PollAnswerHandler

from carpoolerbot import commands, schedules
from carpoolerbot.apscheduler_sqlalchemy_adapter import PTBSQLAlchemyJobStore
from carpoolerbot.poll_report import commands as poll_report_commands
from carpoolerbot.poll_report.handlers import daily_poll_report_callback_handler
from carpoolerbot.poll_report.types import DailyReportCommands
from carpoolerbot.settings import settings
from carpoolerbot.utils import version_command_handler

logger = logging.getLogger(__name__)


async def _set_commands(app: Application) -> None:
    await app.bot.set_my_commands(
        (
            ("poll", "Manually send the weekly Poll."),
            ("get_poll_results", "Get results to last Poll."),
            ("whos_tomorrow", "Return the people on site tomorrow."),
            ("enable_schedule", "Send weekly poll on Sunday and tomorrow's people at set time."),
            ("disable_schedule", "Disable automatic messages."),
            ("version", "Display bot version"),
        ),
    )


def main() -> None:
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    version = importlib.metadata.version("carpoolerbot")
    logger.info("Starting CarpoolerBot version %s", version)

    application = Application.builder().token(settings.TELEGRAM_TOKEN).post_init(_set_commands).build()

    assert application.job_queue
    application.job_queue.scheduler.add_jobstore(PTBSQLAlchemyJobStore(application=application, url=settings.db_url))

    application.add_handler(CommandHandler("poll", commands.poll_cmd))
    application.add_handler(CommandHandler("get_poll_results", poll_report_commands.get_poll_results_cmd))
    application.add_handler(CommandHandler("whos_tomorrow", poll_report_commands.whos_tomorrow_cmd))
    application.add_handler(CommandHandler("enable_schedule", schedules.enable_schedule_cmd))
    application.add_handler(CommandHandler("disable_schedule", schedules.disable_schedule_cmd))
    application.add_handler(PollAnswerHandler(commands.handle_poll_answer))
    application.add_handler(
        CallbackQueryHandler(daily_poll_report_callback_handler, lambda x: x in DailyReportCommands),
    )
    application.add_handler(version_command_handler())

    application.run_polling(allowed_updates=Update.ALL_TYPES)
