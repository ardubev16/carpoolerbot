from dataclasses import dataclass
from enum import IntEnum, auto


@dataclass
class SimpleUser:
    user_id: int
    user_fullname: str
    is_designated_driver: bool

    def mention_html(self) -> str:
        fullname = "🏎 " + self.user_fullname if self.is_designated_driver else self.user_fullname
        return f'<a href="tg://user?id={self.user_id}">{fullname}</a>'


class PollReportType(IntEnum):
    FULL_WEEK = auto()
    SINGLE_DAY = auto()
