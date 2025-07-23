import importlib.metadata
from typing import Any

from telegram import Update, constants
from telegram.ext import BaseHandler, CommandHandler, ContextTypes

type TypedBaseHandler = BaseHandler[Any, ContextTypes.DEFAULT_TYPE, Any]


def version_command_handler() -> TypedBaseHandler:
    async def _version_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
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
