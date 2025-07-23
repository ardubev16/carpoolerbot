import importlib.metadata
import logging

from telegram import Update
from telegram.ext import Application

from carpoolerbot import poll, poll_report, scheduling
from carpoolerbot.apscheduler_sqlalchemy_adapter import PTBSQLAlchemyJobStore
from carpoolerbot.settings import settings
from carpoolerbot.utils import version_command_handler

logger = logging.getLogger(__name__)


async def _set_commands(app: Application) -> None:
    await app.bot.set_my_commands(
        (
            *poll.commands,
            *poll_report.commands,
            *scheduling.commands,
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

    application.add_handlers(poll.handlers())
    application.add_handlers(poll_report.handlers())
    application.add_handlers(scheduling.handlers())
    application.add_handler(version_command_handler())

    application.run_polling(allowed_updates=Update.ALL_TYPES)
