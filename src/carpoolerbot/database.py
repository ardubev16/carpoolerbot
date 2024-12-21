from __future__ import annotations

import functools
import json
import sqlite3
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Concatenate

from carpoolerbot.models import PollReport, PollReportType

if TYPE_CHECKING:
    from collections.abc import Callable

    from telegram import Message, User

    from carpoolerbot.models import PollInstance


class UpsertResult(Enum):
    INSERTED = auto()
    UPDATED = auto()


class InsertResult(Enum):
    SUCCESS = auto()
    ALREADY_EXIST = auto()


class DeleteResult(Enum):
    DELETED = auto()
    NOT_FOUND = auto()


@dataclass
class SimpleUser:
    user_id: int
    user_fullname: str
    is_designated_driver: bool

    def mention_html(self) -> str:
        fullname = "🏎 " + self.user_fullname if self.is_designated_driver else self.user_fullname
        return f'<a href="tg://user?id={self.user_id}">{fullname}</a>'


class DbHelper:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)

    def create_tables(self) -> None:
        tables_init_queries = [
            """\
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER,
                user_fullname TEXT,
                PRIMARY KEY (user_id)
            )""",
            """\
            CREATE TABLE IF NOT EXISTS polls (
                chat_id INTEGER,
                message_id INTEGER,
                poll_id TEXT,
                options JSON,
                PRIMARY KEY (chat_id, poll_id)
            )""",
            """\
            CREATE TABLE IF NOT EXISTS poll_reports (
                poll_id TEXT,
                chat_id INTEGER,
                message_id INTEGER,
                sent_timestamp INTEGER,
                message_type INTEGER,
                PRIMARY KEY (chat_id, message_id),
                FOREIGN KEY (poll_id) REFERENCES polls(poll_id)
            )""",
            """\
            CREATE TABLE IF NOT EXISTS poll_answers (
                poll_id TEXT,
                option_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY (poll_id, option_id, user_id),
                FOREIGN KEY (poll_id) REFERENCES polls(poll_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )""",
            """\
            CREATE TABLE IF NOT EXISTS designated_drivers (
                chat_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY (chat_id, user_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )""",
        ]

        for table_query in tables_init_queries:
            self.conn.execute(table_query)

        self.conn.commit()

    def __del__(self):
        self.conn.close()

    def insert_new_poll(self, poll: PollInstance) -> None:
        self.conn.execute(
            "INSERT INTO polls (chat_id, message_id, poll_id, options) VALUES (?, ?, ?, ?)",
            (poll.chat_id, poll.message_id, poll.poll_id, json.dumps(poll.options)),
        )
        self.conn.commit()

    def get_latest_poll_message_id(self, chat_id: int) -> int | None:
        latest_poll = self.conn.execute(
            "SELECT message_id FROM polls WHERE chat_id = ? ORDER BY message_id DESC",
            (chat_id,),
        ).fetchone()
        if not latest_poll:
            return None

        return latest_poll[0]

    def get_latest_poll_id(self, chat_id: int) -> str | None:
        result = self.conn.execute(
            "SELECT poll_id FROM polls WHERE chat_id = ? ORDER BY message_id DESC",
            (chat_id,),
        ).fetchone()
        if not result:
            return None

        return result[0]

    def _insert_user(self, user: User) -> None:
        self.conn.execute(
            """\
            INSERT INTO users (user_id, user_fullname) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET user_fullname = ?""",
            (user.id, user.full_name, user.full_name),
        )
        self.conn.commit()

    def insert_poll_answer(self, poll_id: str, option_id: int, user: User) -> None:
        self._insert_user(user)
        self.conn.execute(
            "INSERT INTO poll_answers (poll_id, option_id, user_id) VALUES (?, ?, ?)",
            (poll_id, option_id, user.id),
        )
        self.conn.commit()

    def delete_poll_answers(self, poll_id: str, user_id: int) -> None:
        self.conn.execute("DELETE FROM poll_answers WHERE poll_id = ? AND user_id = ?", (poll_id, user_id))
        self.conn.commit()

    def get_poll_results(self, poll_id: str) -> list[tuple[str, list[SimpleUser]]]:
        """Return list which elements are (option_id, list(user_id, user_fullname))."""
        result = self.conn.execute("SELECT chat_id, options FROM polls WHERE poll_id = ?", (poll_id,)).fetchone()

        options = json.loads(result[1])
        answers = self.conn.execute(
            """\
            SELECT
                pa.option_id,
                pa.user_id,
                u.user_fullname,
                EXISTS(SELECT * FROM designated_drivers dd WHERE dd.user_id = pa.user_id AND dd.chat_id = ?)
            FROM poll_answers pa
            JOIN users u ON pa.user_id = u.user_id
            WHERE poll_id = ?""",
            (result[0], poll_id),
        ).fetchall()

        users_by_option: list[list[SimpleUser]] = [[] for _ in options]
        for option_id, user_id, user_fullname, is_designated_driver in answers:
            users_by_option[option_id].append(SimpleUser(user_id, user_fullname, is_designated_driver))

        return list(zip(options, users_by_option, strict=True))

    def insert_designated_driver(self, chat_id: int, user: User) -> InsertResult:
        self._insert_user(user)
        try:
            self.conn.execute("INSERT INTO designated_drivers (chat_id, user_id) VALUES (?, ?)", (chat_id, user.id))
        except sqlite3.IntegrityError:  # UNIQUE constraint failed
            return InsertResult.ALREADY_EXIST
        finally:
            self.conn.commit()

        return InsertResult.SUCCESS

    def delete_designated_driver(self, chat_id: int, user_id: int) -> DeleteResult:
        deleted_rows = self.conn.execute(
            "DELETE FROM designated_drivers WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        ).rowcount
        self.conn.commit()

        if deleted_rows == 0:
            return DeleteResult.NOT_FOUND

        return DeleteResult.DELETED

    def get_poll_reports(self, poll_id: str) -> list[PollReport]:
        poll_reports = self.conn.execute(
            "SELECT chat_id, message_id, sent_timestamp, message_type FROM poll_reports WHERE poll_id = ?",
            (poll_id,),
        ).fetchall()

        return [
            PollReport(poll_id, chat_id, message_id, sent_timestamp, message_type)
            for (chat_id, message_id, sent_timestamp, message_type) in poll_reports
        ]

    def insert_poll_report(
        self,
        poll_id: str,
        report_message: Message,
        message_type: PollReportType,
    ) -> None:
        self.conn.execute(
            "INSERT INTO poll_reports (poll_id, chat_id, message_id, sent_timestamp, message_type) VALUES (?, ?, ?, ?, ?)",  # noqa: E501
            (poll_id, report_message.chat_id, report_message.id, int(report_message.date.timestamp()), message_type),
        )
        self.conn.commit()


def init_db(db_path: str) -> None:
    global _db  # noqa: PLW0603
    _db = DbHelper(db_path)


def with_db[**P, R](f: Callable[Concatenate[DbHelper, P], R]) -> Callable[P, R]:
    @functools.wraps(f)
    def inner(*args: P.args, **kwargs: P.kwargs) -> R:
        return f(_db, *args, **kwargs)

    return inner
