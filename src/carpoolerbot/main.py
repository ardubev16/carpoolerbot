import importlib.metadata
import logging

from telegram import Update
from telegram.ext import Application

from carpoolerbot.apscheduler_sqlalchemy_adapter import PTBSQLAlchemyJobStore
from carpoolerbot.database.session import engine
from carpoolerbot.poll import handlers as poll_handlers
from carpoolerbot.poll_report import handlers as poll_report_handlers
from carpoolerbot.scheduling import handlers as scheduling_handlers
from carpoolerbot.settings import settings
from carpoolerbot.utils import version_command_handler

logger = logging.getLogger(__name__)


async def _set_commands(app: Application) -> None:
    await app.bot.set_my_commands(
        (
            *poll_handlers.commands,
            *poll_report_handlers.commands,
            *scheduling_handlers.commands,
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
    application.job_queue.scheduler.add_jobstore(PTBSQLAlchemyJobStore(application=application, engine=engine))

    application.add_handlers(poll_handlers.handlers())
    application.add_handlers(poll_report_handlers.handlers())
    application.add_handlers(scheduling_handlers.handlers())
    application.add_handler(version_command_handler())

    application.run_polling(allowed_updates=Update.ALL_TYPES)
