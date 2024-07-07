from __future__ import annotations

import functools
import json
import sqlite3
from enum import Enum, auto
from typing import TYPE_CHECKING, Concatenate

if TYPE_CHECKING:
    from collections.abc import Callable

    from carpooler.models import PollInstance


class UpsertResult(Enum):
    INSERTED = auto()
    UPDATED = auto()


class InsertResult(Enum):
    SUCCESS = auto()
    ALREADY_EXIST = auto()


class DeleteResult(Enum):
    DELETED = auto()
    NOT_FOUND = auto()


class DbHelper:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)

    def create_tables(self) -> None:
        tables_init_queries = [
            """\
            CREATE TABLE IF NOT EXISTS polls (
                chat_id INTEGER,
                message_id INTEGER,
                poll_id TEXT,
                options JSON,
                PRIMARY KEY (chat_id, poll_id)
            )""",
            """\
            CREATE TABLE IF NOT EXISTS poll_answers (
                poll_id TEXT,
                option_id INTEGER,
                username TEXT,
                PRIMARY KEY (poll_id, option_id, username),
                FOREIGN KEY (poll_id) REFERENCES polls(poll_id)
            )""",
            """\
            CREATE TABLE IF NOT EXISTS designated_drivers (
                chat_id INTEGER,
                username TEXT,
                PRIMARY KEY (chat_id, username)
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
        if latest_poll:
            return latest_poll[0]

        return None

    def insert_poll_answer(self, poll_id: str, option_id: int, username: str) -> None:
        self.conn.execute(
            "INSERT INTO poll_answers (poll_id, option_id, username) VALUES (?, ?, ?)",
            (poll_id, option_id, username),
        )
        self.conn.commit()

    def delete_poll_answers(self, poll_id: str, username: str) -> None:
        self.conn.execute("DELETE FROM poll_answers WHERE poll_id = ? AND username = ?", (poll_id, username))
        self.conn.commit()

    def get_latest_poll_results(self, chat_id: int) -> list[tuple[str, list[str]]] | None:
        result = self.conn.execute(
            "SELECT poll_id, options FROM polls WHERE chat_id = ? ORDER BY message_id DESC",
            (chat_id,),
        ).fetchone()
        if not result:
            return None

        options = json.loads(result[1])
        answers = self.conn.execute(
            "SELECT option_id, username FROM poll_answers WHERE poll_id = ?",
            (result[0],),
        ).fetchall()

        users_by_option: list[list[str]] = [[] for _ in options]
        for option_id, username in answers:
            users_by_option[option_id].append(username)

        return list(zip(options, users_by_option, strict=True))

    def insert_designated_driver(self, chat_id: int, username: str) -> InsertResult:
        try:
            self.conn.execute("INSERT INTO designated_drivers (chat_id, username) VALUES (?, ?)", (chat_id, username))
        except sqlite3.IntegrityError:  # UNIQUE constraint failed
            return InsertResult.ALREADY_EXIST
        finally:
            self.conn.commit()

        return InsertResult.SUCCESS

    def delete_designated_driver(self, chat_id: int, username: str) -> DeleteResult:
        deleted_rows = self.conn.execute(
            "DELETE FROM designated_drivers WHERE chat_id = ? AND username = ?",
            (chat_id, username),
        ).rowcount
        self.conn.commit()

        if deleted_rows == 0:
            return DeleteResult.NOT_FOUND

        return DeleteResult.DELETED


def init_db(db_path: str) -> None:
    global _db  # noqa: PLW0603
    _db = DbHelper(db_path)


def with_db[**P, R](f: Callable[Concatenate[DbHelper, P], R]) -> Callable[P, R]:
    @functools.wraps(f)
    def inner(*args: P.args, **kwargs: P.kwargs) -> R:
        return f(_db, *args, **kwargs)

    return inner
