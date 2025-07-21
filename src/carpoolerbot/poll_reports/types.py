from enum import IntEnum, StrEnum

from telegram import InlineKeyboardButton


class DailyReportCommands(StrEnum):
    CONFIRM = "daily_msg:confirm"
    REJECT = "daily_msg:reject"
    DRIVE = "daily_msg:drive"
    WORK = "daily_msg:return:work"
    DINNER = "daily_msg:return:dinner"
    LATE = "daily_msg:return:late"


class ReturnTime(IntEnum):
    """Enum representing the return time options for the daily message."""

    AFTER_WORK = 0
    AFTER_DINNER = 1
    LATE = 2


DAILY_MSG_KEYBOARD_DEFAULT = [
    [
        InlineKeyboardButton("✅", callback_data=DailyReportCommands.CONFIRM),
        InlineKeyboardButton("🚗", callback_data=DailyReportCommands.DRIVE),
        InlineKeyboardButton("❌", callback_data=DailyReportCommands.REJECT),
    ],
    [
        InlineKeyboardButton("💼", callback_data=DailyReportCommands.WORK),
        InlineKeyboardButton("🍽", callback_data=DailyReportCommands.DINNER),
        InlineKeyboardButton("🎯", callback_data=DailyReportCommands.LATE),
    ],
]
