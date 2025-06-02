from sqlalchemy import delete
from telegram import User

from carpoolerbot.database.models import DbUser, DesignatedDriver
from carpoolerbot.database.session import Session
from carpoolerbot.database.types import DeleteResult


def insert_designated_driver(chat_id: int, user: User) -> None:
    with Session.begin() as s:
        s.merge(DbUser.from_telegram_user(user))
        s.merge(DesignatedDriver(chat_id=chat_id, user_id=user.id))


def delete_designated_driver(chat_id: int, user: User) -> DeleteResult:
    with Session.begin() as s:
        deleted_rows = s.execute(
            delete(DesignatedDriver).where(DesignatedDriver.chat_id == chat_id, DesignatedDriver.user_id == user.id),
        ).rowcount

    if deleted_rows > 0:
        return DeleteResult.DELETED

    return DeleteResult.NOT_FOUND
