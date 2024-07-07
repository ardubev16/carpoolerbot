from dataclasses import dataclass


@dataclass
class PollInstance:
    chat_id: int
    message_id: int
    poll_id: str
    options: list[str]
