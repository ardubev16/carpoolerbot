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


def help_command_handler() -> TypedBaseHandler:
    async def _help_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        assert update.effective_chat

        message = """\
<b>Carpooler Bot</b> is a Telegram bot for managing carpooling arrangements.

<b>Daily message commands:</b>
- ✅ Confirm your carpooling plans
- 🚗 Indicate that you will drive
- ❌ Reject the carpooling arrangement
- 💼 Indicate you will return right after work
- 🍽 Indicate you will return after dinner
- 🎯 Indicate you will return late"""

        await update.effective_chat.send_message(
            message,
            parse_mode=constants.ParseMode.HTML,
            disable_notification=True,
        )

    return CommandHandler("help", _help_cmd)
