from dataclasses import dataclass
from enum import IntEnum, auto


@dataclass
class PollInstance:
    chat_id: int
    message_id: int
    poll_id: str
    options: list[str]


class PollReportType(IntEnum):
    FULL_WEEK = auto()
    SINGLE_DAY = auto()


@dataclass
class PollReport:
    poll_id: str
    chat_id: int
    message_id: int
    sent_timestamp: int
    message_type: PollReportType
