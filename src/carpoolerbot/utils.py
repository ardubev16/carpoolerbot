from enum import IntEnum

from telegram import Update, constants
from telegram.ext import CommandHandler, ContextTypes


def version_command_handler() -> CommandHandler:
    async def _version_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        import importlib.metadata

        version = importlib.metadata.version("carpoolerbot")
        release_notes_url = f"https://github.com/ardubev16/carpoolerbot/releases/tag/v{version}"
        message = f"""\
Bot version: <code>{version}</code>

To see what's changed checkout the <a href='{release_notes_url}'>Release Notes</a>"""
        assert update.effective_chat
        await update.effective_chat.send_message(
            message,
            parse_mode=constants.ParseMode.HTML,
            disable_notification=True,
        )

    return CommandHandler("version", _version_cmd)


class ReturnTime(IntEnum):
    """Enum representing the return time options for the daily message."""

    AFTER_WORK = 0
    AFTER_DINNER = 1
    LATE = 2
