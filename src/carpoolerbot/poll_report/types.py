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


class NotVotedError(Exception):
    """Exception raised when a user tries to interact with a daily report without voting."""

    def __init__(self, user_id: int, poll_id: str, poll_option_id: int) -> None:
        super().__init__(f"User {user_id} has not voted in poll {poll_id} for option {poll_option_id}.")
        self.user_id = user_id
        self.poll_id = poll_id
        self.poll_option_id = poll_option_id
